"""Evidence-led searches, independent registration records, and quiet notifications."""
import time
import threading
from typing import Literal, Protocol
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, func
from . import db
from .db import (Alert, Observation, Vehicle, StreamEvent, NotificationPreference,
                 NotificationState, InvestigationCase, CaseLink, AppearanceWatch, row_dict)
from .auth import current_user, admin_user, audit
from .service import normalize_plate, get_run, observation_dict, alert_dict, emit
from .review_score import theft_review

router=APIRouter(prefix='/api/v1')
PRIORITY={'critical':0,'high':1,'medium':2}
notification_lock=threading.Lock()

def subject_for(s, alert):
    observation=s.get(Observation,alert.latest_observation_id)
    if observation.status=='accepted' and observation.vehicle_id and alert.match_method!='possible':
        return 'plate:'+s.get(Vehicle,observation.vehicle_id).plate
    return 'observation:'+observation.id

def preference(s,subject,user_id):
    now=time.time()
    rows=list(s.scalars(select(NotificationPreference).where(
        NotificationPreference.subject==subject,NotificationPreference.user_id.in_([user_id,'*']))))
    active=[p for p in rows if p.muted and (p.until is None or p.until>now)]
    return {'muted':bool(active),'stopped':any(p.user_id=='*' for p in active),
            'personal_muted':any(p.user_id==user_id for p in active),
            'until':next((p.until for p in active if p.user_id==user_id),None)}

def decorated_alert(s,a,user):
    d=alert_dict(s,a);subject=subject_for(s,a)
    d.update(subject=subject,notification=preference(s,subject,user['id']))
    trigger=s.get(Observation,a.observation_id)
    q=select(func.count()).select_from(Observation).where(Observation.run_id==a.run_id)
    if a.match_method=='exact' and a.vehicle_id:
        q=q.where(Observation.vehicle_id==a.vehicle_id,Observation.status=='accepted',Observation.observed_at>=trigger.observed_at)
        d['sighting_count']=s.scalar(q)
    else:d['sighting_count']=1
    return d

def alert_sort(a):return (PRIORITY.get(a.priority,3),-a.updated_at,a.id)

def valid_subject(s,subject):
    kind,_,value=subject.partition(':')
    if kind=='plate' and normalize_plate(value)==value and s.scalar(select(Vehicle).where(Vehicle.plate==value)):
        return subject
    if kind=='observation' and s.get(Observation,value):return subject
    raise HTTPException(422,'Choose a stored vehicle or individual candidate.')

class PreferenceInput(BaseModel):
    subject:str=Field(max_length=120)
    action:Literal['mute','unmute','stop','enable','dismiss']
    minutes:Literal[15,60]|None=None

@router.get('/notification-preferences')
def get_preferences(subject:str,user=Depends(current_user)):
    with db.Session() as s:
        valid_subject(s,subject);return preference(s,subject,user['id'])

@router.post('/notification-preferences')
def update_preference(body:PreferenceInput,user=Depends(current_user)):
    if body.action in ['stop','enable'] and user['role']!='admin':
        raise HTTPException(403,'Only an administrator can stop alerts for everyone.')
    with db.Session.begin() as s:
        subject=valid_subject(s,body.subject)
        if body.action!='dismiss':
            owner='*' if body.action in ['stop','enable'] else user['id']
            p=s.scalar(select(NotificationPreference).where(NotificationPreference.user_id==owner,NotificationPreference.subject==subject))
            if not p:p=NotificationPreference(user_id=owner,subject=subject);s.add(p)
            p.muted=body.action in ['mute','stop']
            p.until=time.time()+body.minutes*60 if body.action=='mute' and body.minutes else None
        if body.action in ['dismiss','stop']:
            for a in s.scalars(select(Alert).where(Alert.status!='dismissed')):
                if subject_for(s,a)==subject:a.status='dismissed'
        audit(s,user,'notifications.'+body.action,subject,body.model_dump())
        emit(s,'notifications.preferences');s.flush()
        return preference(s,subject,user['id'])

@router.post('/notifications/poll')
def notifications(user=Depends(current_user)):
    # A durable user cursor prevents duplicate banners across tabs and reconnects.
    with notification_lock,db.Session.begin() as s:
        state=s.get(NotificationState,user['id'])
        if not state:
            state=NotificationState(user_id=user['id'],cursor=s.scalar(select(func.max(StreamEvent.id))) or 0,details={})
            s.add(state);return {'items':[]}
        events=list(s.scalars(select(StreamEvent).where(StreamEvent.id>state.cursor).order_by(StreamEvent.id).limit(1000)))
        details=dict(state.details);delivered=dict(details.get('delivered',{}));subjects=dict(details.get('subjects',{}))
        grouped={};now=time.time()
        for event in events:
            state.cursor=event.id
            if event.kind not in ['alert.created','alert.updated'] or now-event.created_at>30:continue
            a=s.get(Alert,event.payload.get('id'))
            if not a or a.status!='open':continue
            subject=subject_for(s,a);rank=PRIORITY.get(a.priority,2)
            if preference(s,subject,user['id'])['muted']:continue
            if rank>=delivered.get(a.id,99):continue
            previous=subjects.get(subject,{'at':0,'rank':99})
            if now-previous['at']<300 and rank>=previous['rank']:
                delivered[a.id]=rank;continue
            grouped.setdefault(subject,[]).append(a)
        items=[]
        for subject,alerts in grouped.items():
            alerts=sorted({a.id:a for a in alerts}.values(),key=alert_sort)
            a=alerts[0];rank=PRIORITY.get(a.priority,2)
            items.append({'id':a.id,'subject':subject,'priority':a.priority,'message':f'{a.priority.title()} · '+ ' · '.join(dict.fromkeys(x.reason for x in alerts)),'vehicle_id':a.vehicle_id})
            for other in alerts:delivered[other.id]=PRIORITY.get(other.priority,2)
            subjects[subject]={'at':now,'rank':rank}
        # Remove old bookkeeping once episodes no longer exist (retention).
        existing=set(s.scalars(select(Alert.id)))
        state.details={'delivered':{k:v for k,v in delivered.items() if k in existing},
                       'subjects':{k:v for k,v in subjects.items() if now-v['at']<300}}
        return {'items':sorted(items,key=lambda a:PRIORITY.get(a['priority'],3))}

REGISTRY={
 'DL8CAF2041':dict(manufacturer='Honda',model='City',vehicle_class='Motor car',fuel='Petrol',color='White',authority='Delhi — Wazirpur',registration_date='2021-06-18'),
 'DL10CZ7788':dict(manufacturer='Maruti Suzuki',model='Dzire',vehicle_class='Motor car',fuel='Petrol',color='Silver',authority='Delhi — Raja Garden',registration_date='2023-02-11'),
 'HR26DQ9021':dict(manufacturer='Hyundai',model='Creta',vehicle_class='Motor car',fuel='Diesel',color='Blue',authority='Gurugram',registration_date='2022-09-07'),
}
class RegistrationProvider(Protocol):
    def lookup(self,plate:str)->dict:...
class DemoRegistrationProvider:
    def lookup(self,plate):
        record=REGISTRY.get(plate)
        return {'plate':plate,'status':'demo_found' if record else 'unavailable','source':'Demonstration registry',
                'live_connected':False,'updated_at':'2026-09-23','official_url':'https://parivahan.gov.in/parivahan/en/content/license-registration-details',
                'record':dict(record,registration_status='Active — synthetic example') if record else None,
                'message':'Demonstration registration record' if record else 'No demonstration record is available. Live registration lookup is not connected.'}
registration_provider:RegistrationProvider=DemoRegistrationProvider()

@router.get('/registrations/{plate}')
def registration(plate:str,user=Depends(current_user)):
    normalized=normalize_plate(plate)
    if not normalized or not 4<=len(normalized)<=20:raise HTTPException(422,'Enter a registration number.')
    result=registration_provider.lookup(normalized)
    with db.Session.begin() as s:audit(s,user,'registration.lookup',normalized,{'source':result['source'],'status':result['status']})
    return result

COLORS=Literal['white','silver','black','blue','red','green','yellow','orange','brown','grey','unknown']
class Appearance(BaseModel):
    colors:list[COLORS]=Field(default_factory=list,max_length=8)
    regions:dict[str,COLORS]=Field(default_factory=dict)
    pattern:Literal['solid','two-tone','stripes','graphics','contrasting panel','unknown']='unknown'
    features:list[str]=Field(default_factory=list,max_length=12)
    visibility:Literal['clear','partly obscured','heavily obscured','unknown']='unknown'
    plate_visibility:Literal['readable','unreadable','obscured','out of view','visibly absent','unknown']='unknown'
    origin:Literal['model output','operator annotation','demo fixture']='operator annotation'
    @model_validator(mode='after')
    def validate_regions(self):
        if any(k not in ['body','roof','bonnet','doors','unknown'] for k in self.regions):raise ValueError('Unsupported body region.')
        if any(not x.strip() or len(x)>100 for x in self.features):raise ValueError('Feature descriptions must be 1–100 characters.')
        return self

class CandidateQuery(BaseModel):
    colors:list[COLORS]=Field(default_factory=list,max_length=6)
    color_mode:Literal['any','all']='all'
    regions:dict[str,COLORS]=Field(default_factory=dict)
    pattern:str=Field('',max_length=40)
    features:list[str]=Field(default_factory=list,max_length=12)
    visibility:str=Field('',max_length=30)
    plate_visibility:str=Field('',max_length=30)
    vehicle_type:str=Field('',max_length=30)
    make_model:str=Field('',max_length=100)
    camera_ids:list[str]=Field(default_factory=list,max_length=12)
    from_time:float|None=Field(None,allow_inf_nan=False)
    to_time:float|None=Field(None,allow_inf_nan=False)
    run_id:str='current'
    include_unknown:bool=True
    limit:int=Field(50,ge=1,le=200)
    @model_validator(mode='after')
    def valid_window(self):
        if self.from_time is not None and self.to_time is not None and self.from_time>self.to_time:raise ValueError('Start must precede end.')
        return self

def appearance_for(o):
    if o.details.get('appearance'):return o.details['appearance']
    return dict(colors=[o.color] if o.color!='unknown' else [],regions={},features=[],pattern='unknown',visibility='unknown',plate_visibility='readable' if o.plate else 'unknown',origin=o.details.get('attribute_origin','unknown'))

def explain(o,q):
    a=appearance_for(o);matches=[];conflicts=[];unknown=[];distinct=0;body=0;color=0
    def compare(label,requested,observed,kind='distinct'):
        nonlocal distinct,body,color
        if not requested:return
        if not observed or observed=='unknown':unknown.append(label);return
        if str(requested).lower() in str(observed).lower():
            matches.append(label)
            if kind=='distinct':distinct+=1
            elif kind=='body':body+=1
            else:color+=1
        else:conflicts.append(label)
    for feature in q.features:compare(feature,feature,' | '.join(a.get('features',[])))
    for region,value in q.regions.items():compare(region+' '+value,value,a.get('regions',{}).get(region))
    compare('Pattern '+q.pattern,q.pattern,a.get('pattern'))
    compare('Visibility '+q.visibility,q.visibility,a.get('visibility'))
    compare('Plate '+q.plate_visibility,q.plate_visibility,a.get('plate_visibility'))
    compare('Type '+q.vehicle_type,q.vehicle_type,o.vehicle_type,'body')
    compare('Model '+q.make_model,q.make_model,o.details.get('make_model'),'body')
    if q.colors:
        observed=set(a.get('colors',[]))-{'unknown'};requested=set(q.colors)
        if not observed:unknown.append('Colors')
        elif (requested<=observed if q.color_mode=='all' else bool(requested&observed)):
            matches.append('Colors: '+', '.join(q.colors));color+=1
        else:conflicts.append('Colors: '+', '.join(q.colors))
    requested=len(matches)+len(conflicts)+len(unknown)
    match_score=round(100*len(matches)/requested) if requested else 0
    return {'matches':matches,'conflicts':conflicts,'unknown':unknown,'match_score':match_score,'rank':[len(conflicts),-match_score,-distinct,-body,-color], 'appearance':a}

@router.post('/search/candidates')
def search_candidates(q:CandidateQuery,user=Depends(current_user)):
    with db.Session.begin() as s:
        query=select(Observation);run=get_run(s)
        if q.run_id!='all':query=query.where(Observation.run_id== (run.id if q.run_id=='current' else q.run_id))
        if q.camera_ids:query=query.where(Observation.camera_id.in_(q.camera_ids))
        if q.from_time is not None:query=query.where(Observation.observed_at>=q.from_time)
        if q.to_time is not None:query=query.where(Observation.observed_at<=q.to_time)
        groups={}
        for o in s.scalars(query.order_by(Observation.observed_at.desc())):
            x=explain(o,q)
            if x['conflicts'] or (x['unknown'] and not q.include_unknown):continue
            key='vehicle:'+o.vehicle_id if o.vehicle_id and o.status=='accepted' else 'observation:'+o.id
            g=groups.setdefault(key,[]);g.append((o,x))
        items=[]
        for key,group in groups.items():
            group.sort(key=lambda pair:(*pair[1]['rank'],-pair[0].observed_at))
            o,x=group[0]
            items.append({'id':key,'observation':observation_dict(s,o),'explanation':x,'theft_review':theft_review(s,o),
                          'sightings':len(group),'last_seen':max(p[0].observed_at for p in group),
                          'subject':'plate:'+s.get(Vehicle,o.vehicle_id).plate if o.status=='accepted' and o.vehicle_id else 'observation:'+o.id})
        items.sort(key=lambda x:(*x['explanation']['rank'],-(x['theft_review']['score'] or 0),-x['last_seen'],x['id']))
        audit(s,user,'appearance.search','candidates',{'query':q.model_dump(),'results':len(items)})
        return {'items':items[:q.limit],'total':len(items),'label':'Candidate ranking, not an identity probability'}

class CaseInput(BaseModel):
    title:str=Field(min_length=3,max_length=120)
    description:str=Field('',max_length=2000)
    observation_ids:list[str]=Field(default_factory=list,max_length=100)
    criteria:CandidateQuery|None=None

@router.get('/cases')
def cases(user=Depends(current_user)):
    with db.Session() as s:return [row_dict(c) for c in s.scalars(select(InvestigationCase).order_by(InvestigationCase.created_at.desc()))]

@router.post('/cases')
def create_case(body:CaseInput,user=Depends(current_user)):
    with db.Session.begin() as s:
        c=InvestigationCase(title=body.title,description=body.description,created_by=user['id'],criteria=body.criteria.model_dump() if body.criteria else {})
        s.add(c);s.flush()
        for oid in dict.fromkeys(body.observation_ids):
            if not s.get(Observation,oid):raise HTTPException(404,'Observation not found.')
            s.add(CaseLink(case_id=c.id,observation_id=oid,history=[{'action':'proposed','actor':user['id'],'at':time.time(),'reason':'Added as a candidate; identity not established.'}]))
        audit(s,user,'case.create',c.id);emit(s,'case.updated');return row_dict(c)

@router.get('/cases/{case_id}')
def case_detail(case_id:str,user=Depends(current_user)):
    with db.Session.begin() as s:
        c=s.get(InvestigationCase,case_id)
        if not c:raise HTTPException(404,'Case not found.')
        links=[]
        for l in s.scalars(select(CaseLink).where(CaseLink.case_id==case_id)):
            o=s.get(Observation,l.observation_id)
            links.append({**row_dict(l),'observation':observation_dict(s,o) if o else None})
        links.sort(key=lambda l:l['observation']['observed_at'] if l['observation'] else 0)
        audit(s,user,'case.view',c.id)
        return {**row_dict(c),'links':links,'watches':[row_dict(w) for w in s.scalars(select(AppearanceWatch).where(AppearanceWatch.case_id==case_id))]}

class CaseLinkInput(BaseModel):observation_id:str
@router.post('/cases/{case_id}/links')
def add_link(case_id:str,body:CaseLinkInput,user=Depends(current_user)):
    with db.Session.begin() as s:
        if not s.get(InvestigationCase,case_id) or not s.get(Observation,body.observation_id):raise HTTPException(404,'Case or sighting not found.')
        l=s.scalar(select(CaseLink).where(CaseLink.case_id==case_id,CaseLink.observation_id==body.observation_id))
        if not l:
            l=CaseLink(case_id=case_id,observation_id=body.observation_id,history=[{'action':'proposed','actor':user['id'],'at':time.time(),'reason':'Added to case.'}]);s.add(l);s.flush()
            audit(s,user,'case.link',l.id);emit(s,'case.updated')
        return row_dict(l)

class LinkReview(BaseModel):
    status:Literal['proposed','accepted','rejected']
    reason:str=Field(min_length=5,max_length=500)
@router.patch('/cases/{case_id}/links/{link_id}')
def review_link(case_id:str,link_id:str,body:LinkReview,user=Depends(current_user)):
    with db.Session.begin() as s:
        l=s.get(CaseLink,link_id)
        if not l or l.case_id!=case_id:raise HTTPException(404,'Candidate not found.')
        l.status=body.status;l.history=[*l.history,{'action':body.status,'reason':body.reason,'actor':user['id'],'at':time.time()}]
        audit(s,user,'case.review',l.id,body.model_dump());emit(s,'case.updated');return row_dict(l)

class WatchAppearanceInput(BaseModel):
    criteria:CandidateQuery
    hours:int=Field(1,ge=1,le=24)
@router.post('/cases/{case_id}/watch')
def appearance_watch(case_id:str,body:WatchAppearanceInput,user=Depends(admin_user)):
    q=body.criteria
    if not q.camera_ids or q.from_time is None or q.to_time is None or not (q.features or q.regions or q.pattern not in ['', 'solid','unknown']):
        raise HTTPException(422,'Appearance alerts require a camera area, time window, and a distinctive feature or pattern.')
    with db.Session.begin() as s:
        if not s.get(InvestigationCase,case_id):raise HTTPException(404,'Case not found.')
        for old in s.scalars(select(AppearanceWatch).where(AppearanceWatch.case_id==case_id,AppearanceWatch.active==True,AppearanceWatch.expires_at>time.time())):
            if old.criteria==q.model_dump():return row_dict(old)
        w=AppearanceWatch(case_id=case_id,criteria=q.model_dump(),expires_at=time.time()+body.hours*3600);s.add(w);s.flush()
        audit(s,user,'appearance.watch',w.id);return row_dict(w)

@router.delete('/cases/{case_id}/watch/{watch_id}')
def stop_appearance_watch(case_id:str,watch_id:str,user=Depends(admin_user)):
    with db.Session.begin() as s:
        w=s.get(AppearanceWatch,watch_id)
        if not w or w.case_id!=case_id:raise HTTPException(404,'Watch not found.')
        w.active=False;audit(s,user,'appearance.watch.stop',w.id);emit(s,'case.updated')
        return row_dict(w)

def match_appearance_watches(s,o):
    for w in s.scalars(select(AppearanceWatch).where(AppearanceWatch.active==True,AppearanceWatch.expires_at>time.time())):
        q=CandidateQuery(**w.criteria)
        if o.camera_id not in q.camera_ids or not q.from_time<=o.observed_at<=q.to_time:continue
        x=explain(o,q)
        if x['conflicts'] or x['unknown']:continue
        key=f'{o.run_id}:appearance:{w.id}:{o.camera_id}:{o.track_id}'
        if s.scalar(select(Alert).where(Alert.episode_key==key)):continue
        a=Alert(episode_key=key,observation_id=o.id,latest_observation_id=o.id,run_id=o.run_id,priority='medium',category='appearance lead',reason=f'Appearance lead for case {w.case_id[:8]} — review required. '+', '.join(x['matches']),match_method='appearance',status='open',created_at=o.observed_at,updated_at=o.observed_at)
        s.add(a);s.flush();emit(s,'alert.created',{'id':a.id})

@router.patch('/observations/{observation_id}/appearance')
def annotate_appearance(observation_id:str,body:Appearance,user=Depends(current_user)):
    with db.Session.begin() as s:
        o=s.get(Observation,observation_id)
        if not o:raise HTTPException(404,'Observation not found.')
        old=o.details.get('appearance');data=body.model_dump();data['origin']='operator annotation'
        o.details={**o.details,'appearance':data,'appearance_history':[*o.details.get('appearance_history',[]),{'before':old,'after':data,'actor':user['id'],'at':time.time()}]}
        audit(s,user,'appearance.annotate',o.id,{'before':old,'after':data});emit(s,'observation.updated');return observation_dict(s,o)
