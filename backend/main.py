import asyncio, hashlib, json, secrets, time, shutil, math
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func, or_, delete
from PIL import Image, UnidentifiedImageError
from .config import *
from .db import *
from .auth import current_user, admin_user, verify_password, audit
from .service import *
from .seed import seed, sample_manifest, target_sample

pool=None
background=set()
model_state={'status':'loading','error':None}

async def warm_worker():
    from .inference import load_models
    try:
        # Worker initializer caches model instances; do not send model objects across processes.
        await asyncio.get_running_loop().run_in_executor(pool,warm_models)
        model_state.update(status='ready',error=None)
    except Exception as exc:model_state.update(status='error',error=str(exc))

def warm_models():
    from .inference import load_models
    load_models();return True

async def process_job(job_id):
    from .inference import infer_image
    try:
        with Session.begin() as s:
            job=s.get(Job,job_id);job.status='running';path=job.input_path;emit(s,'job.updated',{'id':job_id})
        result=await asyncio.get_running_loop().run_in_executor(pool,infer_image,path)
        with Session.begin() as s:
            job=s.get(Job,job_id);run=get_run(s);ids=[]
            if job.run_id!=run.id:raise ValueError('The demo run changed while inference was processing. Process the sample again.')
            manifest=sample_manifest();sample=next((x for x in manifest['samples'] if x['id']==job.sample_id),None)
            for i,d in enumerate(result['detections']):
                evidence=Evidence(original_path=d['original_path'],plate_path=d['plate_path'],vehicle_path=d['vehicle_path'],sha256=d['sha256'],source=sample['source_url'] if sample else 'User supplied local image',license=sample['license'] if sample else 'User supplied',sample_id=job.sample_id,width=d['width'],height=d['height'],models={**result['models'],'input_sha256':result['input_sha256']})
                s.add(evidence);s.flush()
                data={k:d.get(k) for k in ['raw_plate','ocr_confidence','vehicle_confidence','plate_confidence','vehicle_type','color']}
                data.update(event_key=f'job:{job.id}:{i}',track_id=f'image:{result["input_sha256"][:24]}:{i}:{int(run.state["clock"])}',camera_id=job.camera_id,run_id=run.id,observed_at=run.state['clock'],evidence_id=evidence.id,source_kind='real_inference',details={'vehicle_box':d['vehicle_box'],'plate_box':d['plate_box'],'character_scores':d['character_scores'],'confidence_origin':'model output','camera_location_simulated':True,'source_sample_id':job.sample_id,'inference_seconds':result['duration_seconds']})
                o,_=record_observation(s,data);ids.append(o.id)
                if o.status=='accepted' and o.plate==run.state.get('target_plate') and job.camera_id=='C01' and not run.state.get('target_observation_id'):
                    run.state={**run.state,'target_observation_id':o.id}
            job.status='completed';job.result={'observation_ids':ids,'duration_seconds':result['duration_seconds'],'models':result['models'],'detections':len(ids)}
            emit(s,'job.completed',{'id':job_id});emit(s,'demo.updated')
    except Exception as exc:
        with Session.begin() as s:
            job=s.get(Job,job_id)
            if job:job.status='failed';job.error=str(exc)[:800];emit(s,'job.failed',{'id':job_id})

async def replay_loop():
    previous=time.monotonic();heartbeat=0;maintenance=0
    while True:
        await asyncio.sleep(.5);now=time.monotonic();delta=min(now-previous,2);previous=now
        with Session.begin() as s:
            run=get_run(s)
            if not run:continue
            if now-maintenance>3600:purge_expired(s);maintenance=now
            if now-heartbeat>10:
                for c in s.scalars(select(Camera).where(Camera.status!='offline')):c.heartbeat=time.time()
                heartbeat=now
            if run.state['status']!='running':continue
            state=dict(run.state);state['clock']=min(state['clock']+delta*state['speed'],SCENARIO_START+1440)
            original=s.get(Observation,state.get('target_observation_id'))
            emitted=list(state.get('emitted',[]))
            if original:
                schedule=[(420,'C02'),(840,'C03'),(1440,'C04')]
                for offset,cam in schedule:
                    if state['clock']>=SCENARIO_START+offset and cam not in emitted:
                        if s.get(Camera,cam).status=='offline':
                            emitted.append(cam);state['missing_cameras']=[*state.get('missing_cameras',[]),cam];continue
                        data={k:getattr(original,k) for k in ['raw_plate','ocr_confidence','vehicle_confidence','plate_confidence','vehicle_type','color','evidence_id']}
                        data.update(event_key=f'{run.id}:target:{cam}',track_id=f'target-{cam}',camera_id=cam,run_id=run.id,observed_at=SCENARIO_START+offset,source_kind='replay',details={**original.details,'simulated':True,'source_observation_id':original.id,'evidence_reused':True})
                        record_observation(s,data);emitted.append(cam)
                # Deliberately uncertain fixture: no photographic evidence is claimed for this misread.
                if state['clock']>=SCENARIO_START+1000 and 'possible' not in emitted:
                    raw=original.plate[:-1]+('8' if original.plate[-1]!='8' else '3')
                    record_observation(s,{'event_key':f'{run.id}:target:possible','track_id':'target-possible','camera_id':'C08','run_id':run.id,'observed_at':SCENARIO_START+1000,'raw_plate':raw,'ocr_confidence':.73,'vehicle_confidence':.91,'plate_confidence':.79,'vehicle_type':original.vehicle_type,'color':'unknown','source_kind':'synthetic','details':{'simulated':True,'confidence_origin':'synthetic fixture'}})
                    emitted.append('possible')
            # Background passages continue at scenario-minute intervals.
            minute=int((state['clock']-SCENARIO_START)//60)
            for m in range(state.get('background_minute',0)+1,minute+1):
                cam=['C07','C05','C06','C09','C10'][m%5]
                record_observation(s,{'event_key':f'{run.id}:background:{m}','track_id':f'background-{m}','camera_id':cam,'run_id':run.id,'observed_at':SCENARIO_START+m*60,'raw_plate':f'DL04CX{4000+m}','ocr_confidence':.95,'vehicle_confidence':.93,'plate_confidence':.91,'vehicle_type':'car','color':'silver','source_kind':'synthetic','details':{'confidence_origin':'synthetic fixture','simulated':True}})
            state['background_minute']=minute;state['emitted']=emitted
            if state['clock']>=SCENARIO_START+1440:state['status']='completed'
            run.state=state;emit(s,'demo.tick',{'clock':state['clock']})

def purge_expired(s):
    cutoff=time.time()-RETENTION_DAYS*86400
    # Retention uses ingestion time, never the historical scenario clock.
    old_ids=list(s.scalars(select(Observation.id).where(Observation.ingested_at<cutoff)))
    if old_ids:
        s.execute(delete(Alert).where(or_(Alert.observation_id.in_(old_ids),Alert.latest_observation_id.in_(old_ids))))
        s.execute(delete(Association).where(Association.observation_id.in_(old_ids)))
        s.execute(delete(Observation).where(Observation.id.in_(old_ids)))
    for e in s.scalars(select(Evidence).where(Evidence.created_at<cutoff,Evidence.bundled==False)):
        if s.scalar(select(func.count()).select_from(Observation).where(Observation.evidence_id==e.id)):continue
        for name in ['original_path','plate_path','vehicle_path']:
            raw=getattr(e,name)
            if raw:
                path=Path(raw).resolve()
                shared=s.scalar(select(func.count()).select_from(Evidence).where(Evidence.id!=e.id,or_(Evidence.original_path==raw,Evidence.plate_path==raw,Evidence.vehicle_path==raw)))
                if not shared and path.is_relative_to(EVIDENCE.resolve()):path.unlink(missing_ok=True)
        s.delete(e)
    s.execute(delete(LoginSession).where(LoginSession.expires_at<time.time()))
    for job in s.scalars(select(Job).where(Job.created_at<cutoff,Job.status.in_(['completed','failed']))):
        path=Path(job.input_path).resolve()
        if path.is_relative_to((RUNTIME/'uploads').resolve()):path.unlink(missing_ok=True)
        s.delete(job)
    s.execute(delete(StreamEvent).where(StreamEvent.created_at<cutoff))

@asynccontextmanager
async def lifespan(app):
    global pool
    migrate()
    with Session.begin() as s:
        seed(s);purge_expired(s)
        run=get_run(s)
        if run.state['status']=='running':run.state={**run.state,'status':'paused'}
        for job in s.scalars(select(Job).where(Job.status.in_(['queued','running']))):job.status='failed';job.error='Server restarted. Submit the image again.'
    pool=ProcessPoolExecutor(max_workers=1)
    warm=asyncio.create_task(warm_worker());replay=asyncio.create_task(replay_loop())
    yield
    warm.cancel();replay.cancel()
    for task in background:task.cancel()
    pool.shutdown(wait=False,cancel_futures=True)

app=FastAPI(title='SylRak Delhi',version='0.1.0',lifespan=lifespan)
@app.middleware('http')
async def local_origin(request,call_next):
    origin=request.headers.get('origin')
    if request.method not in ['GET','HEAD','OPTIONS'] and origin and origin not in ['http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000','http://localhost:8000']:
        return Response('Origin not allowed',403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='same-origin'
    return response

class LoginInput(BaseModel):
    username: str=Field(max_length=40)
    password: str=Field(max_length=200)
attempts={}
@app.post('/api/v1/auth/login')
def login(body:LoginInput,response:Response,request:Request):
    key=(request.client.host,body.username);recent=[t for t in attempts.get(key,[]) if t>time.time()-60]
    if len(recent)>=10:raise HTTPException(429,'Too many attempts. Try again in one minute.')
    with Session.begin() as s:
        user=s.get(User,body.username)
        if not user or not verify_password(body.password,user.password_hash):
            attempts[key]=recent+[time.time()];raise HTTPException(401,'Username or password is incorrect.')
        token=secrets.token_urlsafe(32);s.add(LoginSession(token=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires_at=time.time()+8*3600))
        response.set_cookie('sylrak_session',token,httponly=True,samesite='strict',max_age=8*3600)
        d={'id':user.id,'name':user.name,'role':user.role};audit(s,d,'login',user.id);return d
@app.get('/api/v1/auth/me')
def me(user=Depends(current_user)):return user
@app.post('/api/v1/auth/logout')
def logout(request:Request,response:Response,user=Depends(current_user)):
    with Session.begin() as s:s.execute(delete(LoginSession).where(LoginSession.token==hashlib.sha256(request.cookies.get('sylrak_session','').encode()).hexdigest()))
    response.delete_cookie('sylrak_session');return {'ok':True}
@app.get('/api/v1/health')
def health():return {'status':'ok','models':model_state,'map_ready':(ASSETS/'map'/'delhi.pmtiles').exists(),'offline_capable':True}

@app.get('/api/v1/snapshot')
def snapshot(user=Depends(current_user)):
    with Session() as s:
        run=get_run(s);alerts=list(s.scalars(select(Alert).where(Alert.run_id==run.id).order_by(Alert.updated_at.desc())))
        obs=list(s.scalars(select(Observation).where(Observation.run_id==run.id).order_by(Observation.observed_at.desc()).limit(12)))
        return {'run':{'id':run.id,**run.state},'cameras':[row_dict(c) for c in s.scalars(select(Camera).order_by(Camera.id))],'recent':[observation_dict(s,o) for o in obs],'alerts':[alert_dict(s,a) for a in alerts if a.status!='dismissed'][:12],'summary':{'passages':s.scalar(select(func.count()).select_from(Observation).where(Observation.run_id==run.id)),'identified':s.scalar(select(func.count(func.distinct(Observation.vehicle_id))).where(Observation.run_id==run.id,Observation.status=='accepted')),'active_alerts':sum(a.status!='dismissed' for a in alerts),'review_required':s.scalar(select(func.count()).select_from(Observation).where(Observation.run_id==run.id,Observation.status.in_(['possible','conflict']))),'tracked':s.scalar(select(func.count(func.distinct(Observation.vehicle_id))).where(Observation.run_id==run.id,Observation.status=='accepted',Observation.observed_at>=run.state['clock']-900))},'models':model_state}

@app.get('/api/v1/cameras')
def cameras(user=Depends(current_user)):
    with Session() as s:return [row_dict(c) for c in s.scalars(select(Camera).order_by(Camera.id))]
@app.get('/api/v1/cameras/{camera_id}')
def camera_detail(camera_id:str,user=Depends(current_user)):
    with Session() as s:
        c=s.get(Camera,camera_id)
        if not c:raise HTTPException(404,'Camera not found.')
        run=get_run(s);items=s.scalars(select(Observation).where(Observation.camera_id==camera_id,Observation.run_id==run.id).order_by(Observation.observed_at.desc()).limit(30))
        return {**row_dict(c),'observations':[observation_dict(s,o) for o in items]}
class CameraUpdate(BaseModel):status:Literal['online','degraded','offline']
@app.patch('/api/v1/cameras/{camera_id}')
def camera_update(camera_id:str,body:CameraUpdate,user=Depends(admin_user)):
    with Session.begin() as s:
        c=s.get(Camera,camera_id)
        if not c:raise HTTPException(404,'Camera not found.')
        c.status=body.status
        if c.status!='offline':c.heartbeat=time.time()
        audit(s,user,'camera.status',camera_id,body.model_dump());emit(s,'camera.updated',{'id':camera_id});return row_dict(c)

@app.get('/api/v1/observations')
def observations(plate:str='',camera:str='',vehicle_type:str='',color:str='',size_class:str='',make_model:str='',body_style:str='',status:str='',watchlist_status:str='',alert_status:str='',from_time:float|None=None,to_time:float|None=None,run_id:str='',offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),user=Depends(current_user)):
    with Session.begin() as s:
        run=get_run(s);q=select(Observation)
        if run_id:q=q.where(Observation.run_id==(run.id if run_id=='current' else run_id))
        if plate:
            normalized=normalize_plate(plate) or ''
            q=q.where(Observation.plate==normalized if len(normalized)>=9 else Observation.plate.contains(normalized))
        for field,value in [('camera_id',camera),('vehicle_type',vehicle_type),('color',color),('status',status)]:
            if value:q=q.where(getattr(Observation,field)==value)
        for key,value in [('size_class',size_class),('body_style',body_style)]:
            if value:q=q.where(func.lower(func.json_extract(Observation.details,'$.'+key))==value.lower())
        if make_model:q=q.where(func.lower(func.json_extract(Observation.details,'$.make_model')).contains(make_model.lower()))
        if from_time is not None:q=q.where(Observation.observed_at>=from_time)
        if to_time is not None:q=q.where(Observation.observed_at<=to_time)
        if watchlist_status:
            plates=[w.plate for w in active_watchlist(s,run.state['clock']) if watchlist_status=='any' or w.category==watchlist_status]
            q=q.where(Observation.plate.in_(plates))
        if alert_status:
            q=q.where(select(Alert.id).where(Alert.status==alert_status,Alert.run_id==Observation.run_id,or_(Alert.vehicle_id==Observation.vehicle_id,Alert.observation_id==Observation.id,Alert.latest_observation_id==Observation.id)).exists())
        total=s.scalar(select(func.count()).select_from(q.subquery()))
        items=list(s.scalars(q.order_by(Observation.observed_at.desc(),Observation.id).offset(offset).limit(limit)))
        audit(s,user,'search','observations',{'plate':plate,'camera':camera,'vehicle_type':vehicle_type,'color':color,'size_class':size_class,'make_model':make_model,'from':from_time,'to':to_time,'results':total})
        return {'items':[observation_dict(s,o) for o in items],'total':total,'offset':offset,'limit':limit}
@app.get('/api/v1/observations/{observation_id}')
def observation_detail(observation_id:str,user=Depends(current_user)):
    with Session.begin() as s:
        o=s.get(Observation,observation_id)
        if not o:raise HTTPException(404,'Observation not found.')
        audit(s,user,'evidence.view',observation_id);return observation_dict(s,o)

class ObservationInput(BaseModel):
    event_key:str=Field(max_length=200)
    camera_id:str
    run_id:str
    track_id:str=Field(max_length=100)
    observed_at:float
    raw_plate:str|None=Field(None,max_length=32)
    ocr_confidence:float|None=Field(None,ge=0,le=1)
    vehicle_confidence:float|None=Field(None,ge=0,le=1)
    plate_confidence:float|None=Field(None,ge=0,le=1)
    vehicle_type:Literal['car','motorcycle','bus','truck','unknown']='unknown'
    color:Literal['white','silver','black','blue','red','green','yellow','unknown']='unknown'
    source_kind:Literal['synthetic']='synthetic'
    details:dict=Field(default_factory=dict)
    @model_validator(mode='after')
    def finite(self):
        if not math.isfinite(self.observed_at):raise ValueError('Timestamp must be finite.')
        return self
@app.post('/api/v1/observations')
def ingest(body:ObservationInput,user=Depends(admin_user)):
    with Session.begin() as s:
        if body.run_id!=get_run(s).id:raise HTTPException(409,'Demo run has changed.')
        try:o,created=record_observation(s,body.model_dump())
        except ValueError as exc:raise HTTPException(422,str(exc))
        audit(s,user,'observation.ingest',o.id);return {'created':created,'observation':observation_dict(s,o)}

@app.get('/api/v1/vehicles/{vehicle_id}')
def vehicle_detail(vehicle_id:str,run_id:str='current',from_time:float|None=None,to_time:float|None=None,user=Depends(current_user)):
    with Session.begin() as s:
        v=s.get(Vehicle,vehicle_id)
        if not v:raise HTTPException(404,'Vehicle identity not found.')
        run=get_run(s);selected_run=run.id if run_id=='current' else run_id
        q=select(Observation).where(Observation.vehicle_id==v.id)
        if selected_run:q=q.where(Observation.run_id==selected_run)
        if from_time is not None:q=q.where(Observation.observed_at>=from_time)
        if to_time is not None:q=q.where(Observation.observed_at<=to_time)
        items=list(s.scalars(q.order_by(Observation.observed_at)))
        alerts=list(s.scalars(select(Alert).where(Alert.vehicle_id==v.id,Alert.run_id==selected_run).order_by(Alert.updated_at.desc())))
        available=list(s.scalars(select(DemoRun).where(DemoRun.id.in_(select(Observation.run_id).where(Observation.vehicle_id==v.id))).order_by(DemoRun.created_at.desc())))
        audit(s,user,'investigation.view',vehicle_id)
        latest=next((o for o in reversed(items) if o.status=='accepted'),items[-1] if items else None)
        attributes={'vehicle_type':latest.vehicle_type,'color':latest.color,**{k:latest.details.get(k,'unknown') for k in ['make_model','size_class','body_style']}} if latest else {}
        return {**vehicle_dict(s,v,selected_run or None),'attributes':attributes,'observations':[observation_dict(s,o) for o in items],'alerts':[alert_dict(s,a) for a in alerts],'runs':[{'id':r.id,'active':r.active,'created_at':r.created_at} for r in available],'selected_run_id':selected_run}
@app.get('/api/v1/vehicles/{vehicle_id}/trajectory')
def trajectory(vehicle_id:str,run_id:str='current',user=Depends(current_user)):
    with Session() as s:
        if not s.get(Vehicle,vehicle_id):raise HTTPException(404,'Vehicle not found.')
        run=get_run(s);selected_run=run.id if run_id=='current' else run_id;items=list(s.scalars(select(Observation).where(Observation.vehicle_id==vehicle_id,Observation.run_id==selected_run,Observation.status=='accepted').order_by(Observation.observed_at)))
        points=[{'observation_id':o.id,'camera_id':o.camera_id,'time':o.observed_at,'coordinates':[s.get(Camera,o.camera_id).lon,s.get(Camera,o.camera_id).lat]} for o in items]
        return {'points':points,'geometry':{'type':'LineString','coordinates':[p['coordinates'] for p in points]},'connection_kind':'estimated','continuous_tracking':False}
class ReviewInput(BaseModel):
    status:Literal['accepted','rejected']
    reason:str=Field(min_length=3,max_length=500)
@app.patch('/api/v1/associations/{association_id}')
def review(association_id:str,body:ReviewInput,user=Depends(current_user)):
    with Session.begin() as s:
        a=s.get(Association,association_id)
        if not a:raise HTTPException(404,'Association not found.')
        if a.status not in ['possible','conflict']:raise HTTPException(409,'This association is not awaiting review.')
        if body.status=='accepted' and not a.vehicle_id:raise HTTPException(422,'No candidate identity to accept.')
        a.status=body.status;a.reviewed_by=user['id'];a.reason+=' Operator review: '+body.reason
        o=s.get(Observation,a.observation_id);o.status=body.status
        if body.status=='rejected':o.vehicle_id=None
        else:o.vehicle_id=a.vehicle_id;match_watchlists(s,o);route_anomaly(s,o)
        for pending in s.scalars(select(Alert).where(Alert.run_id==o.run_id,Alert.match_method=='possible',or_(Alert.observation_id==o.id,Alert.latest_observation_id==o.id))):
            pending.status='dismissed';pending.reason+=' Association '+body.status+' by operator; see audit log.'
            emit(s,'alert.updated',{'id':pending.id})
        audit(s,user,'association.review',a.id,body.model_dump());emit(s,'association.updated',{'id':a.id});return row_dict(a)

@app.get('/api/v1/alerts')
def alerts(status:str='',user=Depends(current_user)):
    with Session() as s:
        q=select(Alert).where(Alert.run_id==get_run(s).id)
        if status:q=q.where(Alert.status==status)
        return [alert_dict(s,a) for a in s.scalars(q.order_by(Alert.updated_at.desc()))]
class AlertUpdate(BaseModel):status:Literal['open','acknowledged','dismissed']
@app.patch('/api/v1/alerts/{alert_id}')
def alert_update(alert_id:str,body:AlertUpdate,user=Depends(current_user)):
    with Session.begin() as s:
        a=s.get(Alert,alert_id)
        if not a:raise HTTPException(404,'Alert not found.')
        a.status=body.status;audit(s,user,'alert.'+body.status,a.id);emit(s,'alert.updated',{'id':a.id});return alert_dict(s,a)

class WatchInput(BaseModel):
    plate:str=Field(min_length=4,max_length=20)
    category:Literal['stolen','wanted','flagged','blacklisted','suspended']='stolen'
    priority:Literal['critical','high','medium']='critical'
    reason:str=Field(min_length=3,max_length=500)
    reference:str=Field(min_length=3,max_length=80)
    active:bool=True
    valid_from:float|None=None
    valid_until:float|None=None
    @model_validator(mode='after')
    def valid_dates(self):
        if self.valid_from and self.valid_until and self.valid_from>self.valid_until:raise ValueError('Validity end must follow its start.')
        if not normalize_plate(self.plate):raise ValueError('Registration must contain letters or numbers.')
        return self
@app.get('/api/v1/watchlist')
def watchlist(user=Depends(current_user)):
    with Session() as s:return [row_dict(w) for w in s.scalars(select(Watchlist).order_by(Watchlist.created_at.desc()))]
@app.post('/api/v1/watchlist')
def watch_add(body:WatchInput,user=Depends(admin_user)):
    with Session.begin() as s:
        w=Watchlist(**{**body.model_dump(),'plate':normalize_plate(body.plate)});s.add(w);s.flush();audit(s,user,'watchlist.create',w.id);emit(s,'watchlist.updated');return row_dict(w)
@app.put('/api/v1/watchlist/{watch_id}')
def watch_update(watch_id:str,body:WatchInput,user=Depends(admin_user)):
    with Session.begin() as s:
        w=s.get(Watchlist,watch_id)
        if not w:raise HTTPException(404,'Watchlist record not found.')
        for k,v in body.model_dump().items():setattr(w,k,normalize_plate(v) if k=='plate' else v)
        audit(s,user,'watchlist.update',w.id,body.model_dump());emit(s,'watchlist.updated');return row_dict(w)

@app.get('/api/v1/traffic')
def traffic(from_time:float|None=None,to_time:float|None=None,user=Depends(current_user)):
    with Session() as s:
        run=get_run(s);end=to_time if to_time is not None else run.state['clock'];start=from_time if from_time is not None else end-7200
        if start>end:raise HTTPException(422,'Start must precede end.')
        return traffic_analytics(s,run.id,start,end)

@app.get('/api/v1/samples')
def samples(user=Depends(current_user)):
    m=sample_manifest()
    return {'target_sample_id':m.get('target_sample_id'),'items':[{k:v for k,v in x.items() if k not in ['ground_truth','vehicle_group']} for x in m['samples'] if x.get('split')=='demo']}
@app.get('/api/v1/samples/{sample_id}/image')
def sample_image(sample_id:str,user=Depends(current_user)):
    sample=next((x for x in sample_manifest()['samples'] if x['id']==sample_id),None)
    if not sample:raise HTTPException(404,'Sample not found.')
    return FileResponse(ASSETS/'samples'/sample['filename'],media_type='image/jpeg')
@app.post('/api/v1/inference/jobs',status_code=202)
async def submit_job(file:UploadFile|None=File(None),sample_id:str|None=Form(None),camera_id:str=Form('C01'),user=Depends(current_user)):
    if model_state['status']=='error':raise HTTPException(503,'Models unavailable: '+str(model_state['error']))
    with Session() as s:
        camera=s.get(Camera,camera_id)
        if not camera:raise HTTPException(422,'Unknown camera.')
        if camera.status=='offline':raise HTTPException(409,'This simulated camera is offline. Select an online camera.')
        if s.scalar(select(func.count()).select_from(Job).where(Job.status.in_(['queued','running'])))>=4:raise HTTPException(429,'The recognition queue is full. Wait for a job to finish.')
    if sample_id:
        sample=next((x for x in sample_manifest()['samples'] if x['id']==sample_id and x.get('split')=='demo'),None)
        if not sample:raise HTTPException(404,'Demonstration sample not found.')
        path=ASSETS/'samples'/sample['filename']
    elif file:
        content=await file.read(10*1024*1024+1)
        if len(content)>10*1024*1024:raise HTTPException(413,'Use an image smaller than 10 MB.')
        import io
        try:
            with Image.open(io.BytesIO(content)) as img:
                if img.format not in ['JPEG','PNG'] or img.width*img.height>40_000_000:raise ValueError()
                img.verify()
        except Exception:raise HTTPException(422,'Upload a valid JPEG or PNG, up to 40 megapixels.')
        folder=RUNTIME/'uploads';folder.mkdir(exist_ok=True);path=folder/(uid()+'.image');path.write_bytes(content)
    else:raise HTTPException(422,'Select a bundled sample or upload an image.')
    with Session.begin() as s:
        run=get_run(s);job=Job(input_path=str(path),camera_id=camera_id,sample_id=sample_id,run_id=run.id);s.add(job);s.flush();job_id=job.id;audit(s,user,'inference.submit',job_id);emit(s,'job.created',{'id':job_id})
    task=asyncio.create_task(process_job(job_id));background.add(task);task.add_done_callback(background.discard)
    return {'id':job_id,'status':'queued'}
@app.get('/api/v1/inference/jobs/{job_id}')
def job_detail(job_id:str,user=Depends(current_user)):
    with Session() as s:
        job=s.get(Job,job_id)
        if not job:raise HTTPException(404,'Job not found.')
        d=row_dict(job);d.pop('input_path');return d

class DemoInput(BaseModel):
    action:Literal['start','pause','reset','speed']
    speed:Literal[1,6,12,60]=12
@app.post('/api/v1/demo')
def demo(body:DemoInput,user=Depends(admin_user)):
    with Session.begin() as s:
        run=get_run(s)
        if body.action=='reset':
            if s.scalar(select(func.count()).select_from(Job).where(Job.status.in_(['queued','running']))):raise HTTPException(409,'Wait for recognition to finish before resetting.')
            seed(s,reset=True);run=get_run(s)
        else:
            state=dict(run.state)
            if body.action=='start':
                if not state.get('target_observation_id'):raise HTTPException(409,'Recognize the target sample at C01 first. The replay uses its actual OCR result.')
                if state['status']=='completed':raise HTTPException(409,'Reset the completed scenario before starting again.')
                state['status']='running'
            elif body.action=='pause':state['status']='paused'
            else:state['speed']=body.speed
            run.state=state
        audit(s,user,'demo.'+body.action,run.id);emit(s,'demo.updated');return {'id':run.id,**run.state}
@app.get('/api/v1/audit')
def audit_log(user=Depends(admin_user)):
    with Session() as s:return [row_dict(a) for a in s.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]

@app.get('/api/v1/events')
async def events(request:Request,after:int=0,user=Depends(current_user)):
    try:cursor=max(after,int(request.headers.get('last-event-id','0')))
    except ValueError:raise HTTPException(422,'Invalid event cursor.')
    async def stream():
        nonlocal cursor
        last_heartbeat=time.monotonic()
        while not await request.is_disconnected():
            try:current_user(request)
            except HTTPException:yield 'event: session.expired\ndata: {}\n\n';return
            with Session() as s:rows=list(s.scalars(select(StreamEvent).where(StreamEvent.id>cursor).order_by(StreamEvent.id).limit(100)))
            for row in rows:
                cursor=row.id;yield f'id: {row.id}\nevent: update\ndata: {json.dumps({"kind":row.kind,"payload":row.payload})}\n\n'
            if time.monotonic()-last_heartbeat>15:yield ': heartbeat\n\n';last_heartbeat=time.monotonic()
            await asyncio.sleep(.5)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.get('/evidence/{evidence_id}/{kind}')
def evidence_file(evidence_id:str,kind:Literal['original','plate','vehicle'],user=Depends(current_user)):
    with Session() as s:
        e=s.get(Evidence,evidence_id)
        if not e:raise HTTPException(404,'Evidence not found.')
        raw=getattr(e,kind+'_path')
        if not raw:raise HTTPException(404,'This crop is unavailable.')
        path=Path(raw).resolve()
        if not path.is_relative_to(EVIDENCE.resolve()) or not path.exists():raise HTTPException(404,'Evidence file is unavailable.')
        return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'private, max-age=3600'})

(ASSETS/'map').mkdir(parents=True,exist_ok=True)
app.mount('/map-assets',StaticFiles(directory=ASSETS/'map'),name='map-assets')
if (ROOT/'dist').exists():
    app.mount('/assets',StaticFiles(directory=ROOT/'dist'/'assets'),name='web-assets')
    @app.get('/{path:path}')
    def frontend(path:str):
        if path.startswith(('api/','evidence/','map-assets/')):raise HTTPException(404)
        if path=='favicon.svg':return FileResponse(ROOT/'dist'/'favicon.svg',media_type='image/svg+xml')
        return FileResponse(ROOT/'dist'/'index.html')
