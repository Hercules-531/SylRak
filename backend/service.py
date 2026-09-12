"""Observation processing. All callers commit before the SSE reader can see events."""
import re, time, statistics
from collections import Counter, defaultdict
from sqlalchemy import select, func, or_, and_
from .db import *
from .config import EXACT_THRESHOLD, POSSIBLE_THRESHOLD
from .geo import distance_km, CORRIDORS

def normalize_plate(raw):
    return re.sub(r'[^A-Z0-9]', '', (raw or '').upper()) or None
def plate_format(plate):
    if not plate: return 'unreadable'
    if re.fullmatch(r'\d{2}BH\d{4}[A-Z]{1,2}',plate): return 'BH series'
    states={'AN','AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ','HP','HR','JH','JK','KA','KL','LA','LD','MH','ML','MN','MP','MZ','NL','OD','OR','PB','PY','RJ','SK','TN','TR','TS','TG','UK','UP','UT','WB'}
    if plate[:2] in states and re.fullmatch(r'[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}',plate): return 'Indian registration'
    return 'unfamiliar format · review'
def edit_distance(a,b):
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1): cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
def emit(s,kind,payload=None): s.add(StreamEvent(kind=kind,payload=payload or {}))
def get_run(s): return s.scalar(select(DemoRun).where(DemoRun.active==True).limit(1))
def active_watchlist(s,at):
    return list(s.scalars(select(Watchlist).where(Watchlist.active==True,or_(Watchlist.valid_from==None,Watchlist.valid_from<=at),or_(Watchlist.valid_until==None,Watchlist.valid_until>=at))))
def compatible(s,vehicle,data):
    if vehicle.vehicle_type!='unknown' and data.get('vehicle_type','unknown')!='unknown' and vehicle.vehicle_type!=data['vehicle_type']:
        return False,'Vehicle category contradicts previous accepted sightings.'
    if vehicle.color!='unknown' and data.get('color','unknown')!='unknown' and vehicle.color!=data['color']:
        return False,'Reported color contradicts previous accepted sightings; verify supporting attributes.'
    # Check the neighbours on BOTH sides of an out-of-order observation.
    before=s.scalar(select(Observation).where(Observation.vehicle_id==vehicle.id,Observation.status=='accepted',Observation.observed_at<=data['observed_at'],Observation.run_id==data['run_id']).order_by(Observation.observed_at.desc()).limit(1))
    after=s.scalar(select(Observation).where(Observation.vehicle_id==vehicle.id,Observation.status=='accepted',Observation.observed_at>data['observed_at'],Observation.run_id==data['run_id']).order_by(Observation.observed_at).limit(1))
    for other in [before,after]:
        if other and other.camera_id!=data['camera_id']:
            km=distance_km(s.get(Camera,other.camera_id),s.get(Camera,data['camera_id']))
            dt=abs(other.observed_at-data['observed_at'])
            if km>.3 and (dt<1 or km/(dt/3600)>150):
                return False,'Camera separation and timestamps imply over 150 km/h straight-line travel; verify identity or clock.'
    return True,'Plate and camera chronology are compatible.'

def record_observation(s,data):
    existing=s.scalar(select(Observation).where(or_(Observation.event_key==data['event_key'],and_(Observation.run_id==data['run_id'],Observation.camera_id==data['camera_id'],Observation.track_id==data['track_id']))))
    if existing: return existing,False
    if not s.get(Camera,data['camera_id']): raise ValueError('Unknown camera.')
    plate=normalize_plate(data.get('raw_plate'))
    confidence=data.get('ocr_confidence') or 0
    status='unresolved'; reason='No readable plate. This passage contributes to flow only.'; score=None; vehicle=None
    if plate:
        vehicle=s.scalar(select(Vehicle).where(Vehicle.plate==plate))
        if vehicle:
            ok,reason=compatible(s,vehicle,data)
            status='accepted' if confidence>=EXACT_THRESHOLD and ok else ('possible' if ok else 'conflict')
            score=1.0
            if confidence<EXACT_THRESHOLD: reason='Exact text candidate; OCR confidence is below the acceptance threshold. '+reason
        elif confidence>=POSSIBLE_THRESHOLD:
            candidates=[]
            for candidate in s.scalars(select(Vehicle)):
                if len(plate)>=6 and edit_distance(plate,candidate.plate)==1:
                    ok,_=compatible(s,candidate,data)
                    if ok: candidates.append(candidate)
            exact_record=any(w.plate==plate for w in active_watchlist(s,data['observed_at']))
            if len(candidates)==1 and not exact_record:
                vehicle=candidates[0];status='possible';score=1-1/max(len(plate),len(vehicle.plate))
                reason=f'One-character difference from {vehicle.plate}; human verification required. Similarity is not a probability.'
            elif confidence>=EXACT_THRESHOLD and not plate_format(plate).startswith('unfamiliar'):
                vehicle=Vehicle(plate=plate,vehicle_type=data.get('vehicle_type','unknown'),color=data.get('color','unknown'))
                s.add(vehicle);s.flush();status='accepted';score=1.0;reason='New exact plate identity; high-confidence OCR.'
            else: reason='Unfamiliar plate format or uncertain reading; preserve the original text for review.'
        else: reason='OCR confidence is too low for automatic association.'
    obs=Observation(**{k:data.get(k) for k in ['event_key','camera_id','observed_at','run_id','track_id','raw_plate','ocr_confidence','vehicle_confidence','plate_confidence','evidence_id']},plate=plate,vehicle_id=vehicle.id if vehicle else None,status=status,source_kind=data['source_kind'],vehicle_type=data.get('vehicle_type','unknown'),color=data.get('color','unknown'),details=data.get('details',{}))
    s.add(obs);s.flush()
    s.add(Association(observation_id=obs.id,vehicle_id=obs.vehicle_id,status=status,score=score,reason=reason))
    match_watchlists(s,obs)
    if status=='accepted': route_anomaly(s,obs)
    emit(s,'observation.created',{'id':obs.id,'vehicle_id':obs.vehicle_id})
    return obs,True

def match_watchlists(s,obs):
    if not obs.plate: return
    assoc=s.scalar(select(Association).where(Association.observation_id==obs.id))
    canonical=s.get(Vehicle,obs.vehicle_id).plate if obs.vehicle_id else obs.plate
    for entry in active_watchlist(s,obs.observed_at):
        exact=canonical==entry.plate and obs.status=='accepted'
        # An unresolved/conflicting exact string is a review alert, never a confirmed hit.
        possible=not exact and (obs.ocr_confidence or 0)>=POSSIBLE_THRESHOLD and edit_distance(obs.plate,entry.plate)<=1
        if not exact and not possible: continue
        key=f'{obs.run_id}:{entry.id}:'+('exact:'+entry.plate if exact else 'possible:'+str(obs.plate))
        alert=s.scalar(select(Alert).where(Alert.episode_key==key))
        reason=(f'Exact match to demonstration {entry.category} record {entry.reference}. ' if exact else f'Possible match to demonstration record {entry.reference}; verify {obs.plate} against {entry.plate}. ')+entry.reason
        if not alert:
            alert=Alert(episode_key=key,vehicle_id=obs.vehicle_id,watchlist_id=entry.id,observation_id=obs.id,latest_observation_id=obs.id,run_id=obs.run_id,priority=entry.priority if exact else 'medium',category=entry.category,reason=reason,match_method='exact' if exact else 'possible',created_at=obs.observed_at,updated_at=obs.observed_at)
            s.add(alert);s.flush();emit(s,'alert.created',{'id':alert.id})
        else:
            if obs.observed_at>=alert.updated_at:
                alert.latest_observation_id=obs.id;alert.updated_at=obs.observed_at
            if exact and alert.match_method!='exact':
                alert.match_method='exact';alert.priority=entry.priority;alert.reason=reason;alert.vehicle_id=obs.vehicle_id
                alert.status='open';alert.observation_id=obs.id
            emit(s,'alert.updated',{'id':alert.id})

def route_anomaly(s,obs):
    sightings=list(s.scalars(select(Observation).where(Observation.vehicle_id==obs.vehicle_id,Observation.run_id==obs.run_id,Observation.status=='accepted').order_by(Observation.observed_at)))
    for i in range(3,len(sightings)):
        group=sightings[i-3:i+1];a,b,c,d=group
        if a.camera_id==c.camera_id and b.camera_id==d.camera_id and a.camera_id!=b.camera_id and d.observed_at-a.observed_at<=1200:
            key=f'{obs.run_id}:repeat-route:{obs.vehicle_id}'
            if not s.scalar(select(Alert).where(Alert.episode_key==key)):
                alert=Alert(episode_key=key,vehicle_id=obs.vehicle_id,observation_id=d.id,latest_observation_id=d.id,run_id=obs.run_id,priority='medium',category='route pattern',reason=f'Repeated movement {a.camera_id} → {b.camera_id} → {c.camera_id} → {d.camera_id} in {int((d.observed_at-a.observed_at)/60)} minutes. Rule: A → B → A → B within 20 minutes. Review context; this is not evidence of an offence.',match_method='rule',created_at=d.observed_at,updated_at=d.observed_at)
                s.add(alert);s.flush();emit(s,'alert.created',{'id':alert.id})

def observation_dict(s,o):
    d=row_dict(o);camera=s.get(Camera,o.camera_id)
    d['camera']=row_dict(camera)
    v=s.get(Vehicle,o.vehicle_id) if o.vehicle_id else None
    d['canonical_plate']=v.plate if v else None
    a=s.scalar(select(Association).where(Association.observation_id==o.id))
    d['association']=row_dict(a) if a else None
    d['format']=plate_format(o.plate)
    if o.evidence_id:
        e=s.get(Evidence,o.evidence_id)
        d['evidence']={k:v for k,v in row_dict(e).items() if not k.endswith('_path')}
        d['evidence'].update({'original_url':f'/evidence/{e.id}/original','plate_url':f'/evidence/{e.id}/plate' if e.plate_path else None,'vehicle_url':f'/evidence/{e.id}/vehicle' if e.vehicle_path else None})
    else: d['evidence']=None
    return d
def alert_dict(s,a):
    d=row_dict(a);o=s.get(Observation,a.latest_observation_id);d['observation']=observation_dict(s,o)
    entry=s.get(Watchlist,a.watchlist_id) if a.watchlist_id else None
    d['watchlist']=row_dict(entry) if entry else None
    return d
def vehicle_dict(s,v,run_id=None):
    query=select(Observation).where(Observation.vehicle_id==v.id)
    if run_id: query=query.where(Observation.run_id==run_id)
    items=list(s.scalars(query.order_by(Observation.observed_at)))
    accepted=[o for o in items if o.status=='accepted']
    return {**row_dict(v),'first_seen':accepted[0].observed_at if accepted else None,'last_seen':accepted[-1].observed_at if accepted else None,'sightings':len(accepted),'cameras':len(set(o.camera_id for o in accepted)),'possible_matches':len(items)-len(accepted)}
def traffic_analytics(s,run_id,from_time,to_time):
    observations=list(s.scalars(select(Observation).where(Observation.run_id==run_id,Observation.observed_at>=from_time,Observation.observed_at<=to_time).order_by(Observation.observed_at)))
    cameras=list(s.scalars(select(Camera)))
    counts=Counter(o.camera_id for o in observations);buckets=Counter(int(o.observed_at//300)*300 for o in observations)
    trajectories=defaultdict(list)
    for o in observations:
        if o.status=='accepted' and o.vehicle_id: trajectories[o.vehicle_id].append(o)
    od=Counter();travel=defaultdict(list)
    for group in trajectories.values():
        trips=[];current=[]
        for o in group:
            if current and o.observed_at-current[-1].observed_at>1800: trips.append(current);current=[]
            current.append(o)
        if current: trips.append(current)
        for trip in trips:
            if len(trip)>1 and trip[0].camera_id!=trip[-1].camera_id: od[(trip[0].camera_id,trip[-1].camera_id)]+=1
            for a,b in zip(trip,trip[1:]):
                dt=b.observed_at-a.observed_at
                if dt>0: travel[(a.camera_id,b.camera_id)].append(dt)
    corridors=[]
    for c in CORRIDORS:
        durations=travel[(c['from'],c['to'])];median=statistics.median(durations) if durations else None
        corridors.append({**c,'samples':len(durations),'median_seconds':median,'estimated_kmh':round(c['km']/(median/3600),1) if median else None,'congestion':len(durations)>=3 and median>1.5*c['baseline_seconds']})
    return {'passages':len(observations),'identified_vehicles':len(trajectories),'from_time':from_time,'to_time':to_time,'coverage':{'online':sum(c.status=='online' for c in cameras),'degraded':sum(c.status=='degraded' for c in cameras),'offline':sum(c.status=='offline' for c in cameras),'total':len(cameras)},'camera_flow':[{**row_dict(c),'passages':counts[c.id]} for c in cameras],'buckets':[{'time':t,'count':buckets[t]} for t in range(int(from_time//300)*300,int(to_time//300)*300+1,300)],'od':[{'from':a,'to':b,'count':n} for (a,b),n in od.most_common(12)],'corridors':corridors,'unreadable':sum(not o.plate for o in observations)}
