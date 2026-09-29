"""Indexed vehicle marks: stickers, glass damage and broken parts logged per sighting.

Demonstration only. Marks are operator logs, clearly labeled model suggestions, or demo
fixtures; no detector runs. Detectability estimates what a 1080p lane camera could resolve.
"""
import re, time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, or_
from . import db
from .db import Observation, Vehicle, VehicleMark, row_dict
from .auth import current_user, audit
from .service import get_run, observation_dict, emit

router=APIRouter(prefix='/api/v1')

CATEGORIES=['sticker','decal / wrap','glass damage','broken part','dent','scratch','accessory','other']
PARTS=['windshield','rear glass','side window','bonnet','roof','front bumper','rear bumper','left doors','right doors',
       'headlight','tail light','wing mirror','boot / tailgate','wheel','plate area','other']
# A 1.7 m wide car spans roughly 500 px of a 1080p lane view: about 3.4 mm per pixel.
MM_PER_PIXEL=3.4
BANDS=[
    {'id':'reliable','label':'Reliable','min_cm':30,'note':'Large decals, wraps, colored panels'},
    {'id':'mostly','label':'Mostly detectable','min_cm':20,'note':'Broken lights, missing bumpers, large dents; flat light hides dents'},
    {'id':'angle-dependent','label':'From the right angle','min_cm':8,'note':'Stickers on glass or bumpers'},
    {'id':'glare-limited','label':'Sometimes','min_cm':None,'note':'Cracked glass; reflections interfere'},
    {'id':'close-up only','label':'Close-up only','min_cm':0,'note':'Chips and small damage need a checkpoint or handheld photo'},
    {'id':'unknown','label':'Size not recorded','min_cm':None,'note':'Add an approximate size to estimate detectability'},
]
Category=Literal['sticker','decal / wrap','glass damage','broken part','dent','scratch','accessory','other']
Part=Literal['windshield','rear glass','side window','bonnet','roof','front bumper','rear bumper','left doors','right doors',
             'headlight','tail light','wing mirror','boot / tailgate','wheel','plate area','other']

def label_key(label):return re.sub(r'\s+',' ',label.strip().lower())
def pixels(size_cm):return None if size_cm is None else round(size_cm*10/MM_PER_PIXEL)
def detectability(category,size_cm):
    if size_cm is None:return 'unknown'
    if size_cm<8:return 'close-up only'
    if category=='glass damage':return 'glare-limited'
    return 'reliable' if size_cm>=30 else 'mostly' if size_cm>=20 else 'angle-dependent'

def mark_dict(s,m,full=False):
    d=row_dict(m);d['pixels']=pixels(m.size_cm)
    o=s.get(Observation,m.observation_id);v=s.get(Vehicle,m.vehicle_id) if m.vehicle_id else None
    d['plate']=v.plate if v else o.plate if o else None
    if full and o:d['observation']=observation_dict(s,o)
    elif o:d['observation']={'id':o.id,'camera_id':o.camera_id,'observed_at':o.observed_at,'run_id':o.run_id,'make_model':o.details.get('make_model')}
    return d

class MarkInput(BaseModel):
    category:Category
    part:Part
    label:str=Field(min_length=3,max_length=100)
    size_cm:float|None=Field(None,gt=0,le=500,allow_inf_nan=False)
    notes:str=Field('',max_length=500)
    origin:Literal['operator log','model suggestion']='operator log'
    @field_validator('label')
    @classmethod
    def trimmed(cls,v):
        if len(v.strip())<3:raise ValueError('Describe the feature in at least 3 characters.')
        return v.strip()

def create_mark(s,o,body,actor):
    key=label_key(body.label)
    if s.scalar(select(VehicleMark).where(VehicleMark.observation_id==o.id,VehicleMark.label_key==key)):
        raise HTTPException(409,'This feature is already logged on this sighting.')
    status='suggested' if body.origin=='model suggestion' else 'confirmed'
    m=VehicleMark(observation_id=o.id,vehicle_id=o.vehicle_id if o.status=='accepted' else None,run_id=o.run_id,
                  category=body.category,part=body.part,label=body.label,label_key=key,size_cm=body.size_cm,
                  detectability=detectability(body.category,body.size_cm),origin=body.origin,status=status,notes=body.notes,
                  created_by=actor,history=[{'action':'logged','status':status,'actor':actor,'at':time.time()}])
    s.add(m);s.flush();return m

@router.get('/marks/taxonomy')
def taxonomy(user=Depends(current_user)):
    return {'categories':CATEGORIES,'parts':PARTS,'bands':BANDS,'mm_per_pixel':MM_PER_PIXEL,
            'camera_assumption':'1080p lane camera; a 1.7 m wide car spans about 500 px'}

@router.post('/observations/{observation_id}/marks')
def log_mark(observation_id:str,body:MarkInput,user=Depends(current_user)):
    with db.Session.begin() as s:
        o=s.get(Observation,observation_id)
        if not o:raise HTTPException(404,'Observation not found.')
        m=create_mark(s,o,body,user['id'])
        audit(s,user,'mark.log',m.id,body.model_dump());emit(s,'mark.updated',{'id':m.id})
        return mark_dict(s,m)

@router.get('/observations/{observation_id}/marks')
def observation_marks(observation_id:str,user=Depends(current_user)):
    with db.Session() as s:
        rows=s.scalars(select(VehicleMark).where(VehicleMark.observation_id==observation_id).order_by(VehicleMark.created_at))
        return [mark_dict(s,m) for m in rows]

@router.get('/vehicles/{vehicle_id}/marks')
def vehicle_marks(vehicle_id:str,user=Depends(current_user)):
    with db.Session() as s:
        if not s.get(Vehicle,vehicle_id):raise HTTPException(404,'Vehicle identity not found.')
        rows=s.scalars(select(VehicleMark).where(VehicleMark.vehicle_id==vehicle_id).order_by(VehicleMark.created_at))
        return [mark_dict(s,m,full=True) for m in rows]

class MarkReview(BaseModel):
    status:Literal['confirmed','suggested','rejected']
    reason:str=Field(min_length=5,max_length=500)

@router.patch('/marks/{mark_id}')
def review_mark(mark_id:str,body:MarkReview,user=Depends(current_user)):
    with db.Session.begin() as s:
        m=s.get(VehicleMark,mark_id)
        if not m:raise HTTPException(404,'Feature log not found.')
        m.status=body.status;m.history=[*m.history,{'action':body.status,'reason':body.reason,'actor':user['id'],'at':time.time()}]
        audit(s,user,'mark.review',m.id,body.model_dump());emit(s,'mark.updated',{'id':m.id})
        return mark_dict(s,m)

def filtered(query,category='',part='',text=''):
    if category:query=query.where(VehicleMark.category==category)
    if part:query=query.where(VehicleMark.part==part)
    if text.strip():query=query.where(VehicleMark.label_key.contains(label_key(text)))
    return query

def feature_filter(category='',part='',text=''):
    """Condition for sightings of a vehicle (or an unplated sighting) with a matching active feature."""
    marks=filtered(select(VehicleMark.vehicle_id,VehicleMark.observation_id).where(VehicleMark.status!='rejected'),category,part,text).subquery()
    return or_(Observation.vehicle_id.in_(select(marks.c.vehicle_id).where(marks.c.vehicle_id.is_not(None))),Observation.id.in_(select(marks.c.observation_id)))

def features_for(s,o,category='',part='',text=''):
    own=VehicleMark.observation_id==o.id
    rows=s.scalars(select(VehicleMark).where(VehicleMark.status!='rejected',or_(own,VehicleMark.vehicle_id==o.vehicle_id) if o.vehicle_id and o.status=='accepted' else own).order_by(VehicleMark.created_at))
    # Features that match the active search come first so the table shows why a row matched.
    matches=lambda m:(not category or m.category==category) and (not part or m.part==part) and label_key(text) in m.label_key
    return [{k:getattr(m,k) for k in ['id','category','part','label','detectability','status']} for m in sorted(rows,key=lambda m:not matches(m))]

def scoped(s,run_id):
    q=select(VehicleMark)
    if run_id!='all':q=q.where(VehicleMark.run_id==(get_run(s).id if run_id=='current' else run_id))
    return q

@router.get('/marks/index')
def mark_index(run_id:str='current',user=Depends(current_user)):
    """Facet counts over confirmed and suggested marks; rejected logs stay out of the index."""
    with db.Session() as s:
        base=scoped(s,run_id).where(VehicleMark.status!='rejected').subquery()
        def facet(column):return {k:n for k,n in s.execute(select(column,func.count()).group_by(column).order_by(func.count().desc()))}
        labels=s.execute(select(base.c.label_key,func.min(base.c.label),func.min(base.c.category),func.count(),
                                func.count(func.distinct(base.c.vehicle_id))).group_by(base.c.label_key).order_by(func.count().desc(),base.c.label_key).limit(12))
        return {'total':s.scalar(select(func.count()).select_from(base)),
                'vehicles':s.scalar(select(func.count(func.distinct(base.c.vehicle_id)))),
                'unidentified_sightings':s.scalar(select(func.count(func.distinct(base.c.observation_id))).where(base.c.vehicle_id.is_(None))),
                'category':facet(base.c.category),'part':facet(base.c.part),'detectability':facet(base.c.detectability),'status':facet(base.c.status),
                'labels':[{'label':l,'category':c,'count':n,'vehicles':v} for _,l,c,n,v in labels]}

@router.get('/marks/search')
def search_marks(category:str='',part:str='',q:str='',detectability:str='',status:Literal['confirmed','suggested','rejected','active']='active',
                 camera_id:str='',run_id:str='current',limit:int=100,user=Depends(current_user)):
    limit=max(1,min(limit,200))
    with db.Session.begin() as s:
        query=scoped(s,run_id)
        query=filtered(query,category,part,q)
        if detectability:query=query.where(VehicleMark.detectability==detectability)
        query=query.where(VehicleMark.status!='rejected') if status=='active' else query.where(VehicleMark.status==status)
        if camera_id:query=query.where(VehicleMark.observation_id.in_(select(Observation.id).where(Observation.camera_id==camera_id)))
        rows=list(s.scalars(query.join(Observation,Observation.id==VehicleMark.observation_id).order_by(Observation.observed_at.desc())))
        audit(s,user,'mark.search','marks',{'category':category,'part':part,'q':q,'results':len(rows)})
        return {'items':[mark_dict(s,m,full=True) for m in rows[:limit]],'total':len(rows),
                'vehicles':len({m.vehicle_id for m in rows if m.vehicle_id}),
                'label':'Logged visible features. A shared feature does not establish identity.'}

FIXTURES=[
    # (event key suffix, category, part, label, size_cm, origin, notes)
    ('seed:0:1','sticker','rear glass','Ganesh sticker, top-left of rear glass',10,'demo fixture','Orange circular sticker.'),
    ('seed:0:2','broken part','tail light','Cracked right tail light',20,'demo fixture','Red lens partly missing.'),
    ('watch-preview','glass damage','windshield','Windshield chip, driver side',1,'model suggestion','Suggested from a close-up frame; needs checkpoint confirmation.'),
    ('appearance:two-tone-0','decal / wrap','right doors','Red door panel wrap',80,'demo fixture',''),
    ('appearance:two-tone-1','sticker','rear glass','"Baby on board" sticker',12,'demo fixture','Yellow square sticker.'),
    ('appearance:dzire-0','decal / wrap','left doors','Cab operator decal on rear doors',35,'demo fixture','Distinguishes this white Dzire from similar cars.'),
    ('appearance:dzire-2','dent','front bumper','Left bumper dent',25,'demo fixture',''),
    ('appearance:cover-before','broken part','wing mirror','Missing right wing mirror',20,'demo fixture',''),
]
GENERIC=[('scratch','left doors','Long scratch along left doors',60),('sticker','windshield','College parking permit sticker',8),
         ('broken part','front bumper','Hanging front bumper, right corner',50),('dent','bonnet','Bonnet dent near badge',30),
         ('glass damage','windshield','Cracked windshield, passenger side',40),('sticker','rear bumper','Political party bumper sticker',15)]

def mark_fixtures(s,run):
    """Idempotent demo marks for the active run; later sightings of each vehicle keep them indexed."""
    for suffix,category,part,label,size,origin,notes in FIXTURES:
        o=s.scalar(select(Observation).where(Observation.event_key==f'{run.id}:{suffix}'))
        if o:add_fixture(s,o,category,part,label,size,origin,notes)
    cars=s.scalars(select(Observation).where(Observation.run_id==run.id,Observation.event_key.like(f'{run.id}:seed:%:0'),
                   Observation.vehicle_type=='car',Observation.status=='accepted',Observation.plate.not_in(['DL8CAF2041','DL3CBR8820'])).order_by(Observation.observed_at))
    for o,(category,part,label,size) in zip(cars,GENERIC):add_fixture(s,o,category,part,label,size,'demo fixture','')

def add_fixture(s,o,category,part,label,size,origin,notes):
    if s.scalar(select(VehicleMark).where(VehicleMark.observation_id==o.id,VehicleMark.label_key==label_key(label))):return
    status='suggested' if origin=='model suggestion' else 'confirmed'
    s.add(VehicleMark(observation_id=o.id,vehicle_id=o.vehicle_id if o.status=='accepted' else None,run_id=o.run_id,category=category,part=part,
                      label=label,label_key=label_key(label),size_cm=size,detectability=detectability(category,size),origin=origin,status=status,
                      notes=notes,created_by='demo',history=[{'action':'logged','status':status,'actor':'demo','at':time.time()}]))
