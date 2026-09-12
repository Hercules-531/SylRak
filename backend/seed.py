import json, random, time
from pathlib import Path
from sqlalchemy import select, delete
from .db import *
from .geo import CAMERAS
from .config import ASSETS, SCENARIO_START
from .service import record_observation, emit
from .auth import init_users

def sample_manifest():
    path=ASSETS/'samples'/'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'samples':[],'target_sample_id':None}
def target_sample():
    m=sample_manifest();return next((x for x in m['samples'] if x['id']==m.get('target_sample_id')),None)
def seed(s,reset=False):
    init_users(s)
    if s.scalar(select(DemoRun).where(DemoRun.active==True)) and not reset:return
    if reset:
        # Archive previous runs so plate queries keep their historical evidence.
        for previous in s.scalars(select(DemoRun).where(DemoRun.active==True)):
            previous.active=False;previous.state={**previous.state,'status':'archived'}
    for id,name,road,lat,lon,direction,status in CAMERAS:
        camera=s.get(Camera,id)
        if not camera:s.add(Camera(id=id,name=name,road=road,lat=lat,lon=lon,direction=direction,status=status,heartbeat=time.time()-(240 if status=='offline' else 0)))
    sample=target_sample();target=sample.get('ground_truth') if sample else None
    for plate,category,reason,ref in [(target,'stolen','Synthetic training record. No real-world allegation.','DEMO-ST-001'),('DL8CAF2041','wanted','Synthetic training record for operator review.','DEMO-W-002'),('DL3CBR8820','flagged','Synthetic checkpoint review record.','DEMO-F-003')]:
        if plate and not s.scalar(select(Watchlist).where(Watchlist.reference==ref)):
            s.add(Watchlist(plate=plate,category=category,reason=reason,reference=ref,priority='critical' if category in ['stolen','wanted'] else 'high'))
    run=DemoRun(state={'status':'idle','clock':SCENARIO_START,'speed':12,'target_observation_id':None,'emitted':[],'seed':26127,'target_plate':target,'target_sample_id':sample['id'] if sample else None})
    s.add(run);s.flush()
    rng=random.Random(26127)
    # Coherent per-vehicle journeys; camera events are not independent random noise.
    routes=[['C01','C02','C03','C04'],['C07','C01','C02','C11','C05'],['C08','C09','C10'],['C05','C06','C03']]
    entries=[]
    for i in range(210):
        plate=('DL8CAF2041' if i==0 else 'DL3CBR8820' if i==1 else f'{["DL","HR","UP","RJ"][i%4]}{i%12+1:02d}{["CA","AB","BT","CX"][i%4]}{1000+i*17:04d}')
        route=routes[i%len(routes)];start=SCENARIO_START-rng.randint(2000,7000)
        vehicle_type=rng.choices(['car','motorcycle','bus','truck'],[62,24,8,6])[0]
        color=rng.choice(['white','silver','black','blue','red','unknown'])
        catalog={
            'car': [('Maruti Suzuki Swift','compact','hatchback'),('Honda City','mid-size','sedan'),('Hyundai Creta','mid-size','SUV'),('Tata Nexon','compact','SUV')],
            'motorcycle': [('Bajaj Pulsar','two-wheeler','motorcycle'),('TVS Apache','two-wheeler','motorcycle')],
            'bus': [('Tata Starbus','large','city bus')],
            'truck': [('Ashok Leyland Partner','large','goods carrier')],
        }
        make_model,size_class,body_style=rng.choice(catalog[vehicle_type])
        if i==0:vehicle_type,color,make_model,size_class,body_style='car','white','Honda City','mid-size','sedan'
        for j,cam in enumerate(route):
            if j:start+=rng.randint(200,480)
            if start>SCENARIO_START:break
            readable=i%19!=0 or i==0
            entries.append({'event_key':f'{run.id}:seed:{i}:{j}','camera_id':cam,'observed_at':start,'run_id':run.id,'track_id':f'seed-{i}-{j}','raw_plate':plate if readable else None,'ocr_confidence':round(rng.uniform(.91,.995),4) if readable else None,'vehicle_confidence':round(rng.uniform(.8,.99),4),'plate_confidence':round(rng.uniform(.8,.99),4) if readable else None,'vehicle_type':vehicle_type,'color':color,'source_kind':'synthetic','details':{'simulated':True,'confidence_origin':'synthetic fixture','camera_location_simulated':True,'make_model':make_model,'size_class':size_class,'body_style':body_style,'attribute_origin':'seeded demonstration metadata'}})
    # Seed one exact watchlist episode and one review candidate in the recent window.
    entries += [{'event_key':f'{run.id}:watch-preview','camera_id':'C09','observed_at':SCENARIO_START-110,'run_id':run.id,'track_id':'watch-preview','raw_plate':'DL8CAF2041','ocr_confidence':.97,'vehicle_confidence':.95,'plate_confidence':.94,'vehicle_type':'car','color':'white','source_kind':'synthetic','details':{'confidence_origin':'synthetic fixture','simulated':True,'make_model':'Honda City','size_class':'mid-size','body_style':'sedan','attribute_origin':'seeded demonstration metadata'}}, {'event_key':f'{run.id}:possible-preview','camera_id':'C02','observed_at':SCENARIO_START-50,'run_id':run.id,'track_id':'possible-preview','raw_plate':'DL3CBR882O','ocr_confidence':.74,'vehicle_confidence':.92,'plate_confidence':.86,'vehicle_type':'car','color':'unknown','source_kind':'synthetic','details':{'confidence_origin':'synthetic fixture','simulated':True,'make_model':'unknown','size_class':'unknown','body_style':'unknown','attribute_origin':'seeded demonstration metadata'}}]
    for data in sorted(entries,key=lambda d:d['observed_at']):record_observation(s,data)
    emit(s,'demo.reset',{'run_id':run.id})
