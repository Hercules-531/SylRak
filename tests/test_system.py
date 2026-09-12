import asyncio,os,time
import pytest
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from backend import main
from backend.db import *
from backend.service import *
from backend.config import SCENARIO_START as T
from backend.seed import seed
from backend.inference import fuse_readings,deduplicate_detections

def event(n,plate='DL01AB1234',cam='C01',at=0,confidence=.98,**changes):
    return dict(event_key=str(n),track_id=str(n),camera_id=cam,run_id='run',observed_at=T+at,raw_plate=plate,ocr_confidence=confidence,source_kind='synthetic',vehicle_type='car',color='unknown',**changes)
def watch(s,plate='DL01AB1234',until=None):
    w=Watchlist(plate=plate,category='stolen',priority='critical',reason='Test fixture',reference='DEMO-TEST',valid_until=until);s.add(w);s.flush();return w

def test_normalization_does_not_rewrite_ambiguous_characters():
    assert normalize_plate(' dl 01-ab 1234 ')=='DL01AB1234'
    assert normalize_plate('KLO1')=='KLO1'
    assert plate_format('22BH1234AB')=='BH series'
    assert plate_format('DL8CAF2041')=='Indian registration'
    assert plate_format('1144').startswith('unfamiliar')

def test_idempotent_passage_and_unreadable_count(database):
    with database.begin() as s:
        a,new=record_observation(s,event(1,None));assert new and a.vehicle_id is None
        b,new=record_observation(s,{**event(2,None),'track_id':'1'});assert not new and a.id==b.id
        assert traffic_analytics(s,'run',T-1,T+1)['passages']==1

def test_exact_episode_updates_only_accepted_location(database):
    with database.begin() as s:
        watch(s)
        for n,cam,at in [(1,'C01',0),(2,'C02',420),(3,'C03',840),(4,'C04',1440)]:record_observation(s,event(n,cam=cam,at=at))
        possible,_=record_observation(s,event(5,plate='DL01AB1235',cam='C09',at=1700,confidence=.73))
        assert possible.status=='possible'
        exact=list(s.scalars(select(Alert).where(Alert.match_method=='exact')));assert len(exact)==1
        assert s.get(Observation,exact[0].latest_observation_id).camera_id=='C04'
        assert len(list(s.scalars(select(Alert))))==2

def test_low_confidence_and_high_confidence_fuzzy_need_review(database):
    with database.begin() as s:
        record_observation(s,event(1))
        a,_=record_observation(s,event(2,confidence=.5));assert a.status=='possible'
        b,_=record_observation(s,event(3,plate='DL01AB1235',confidence=.99));assert b.status=='possible'
        bad,_=record_observation(s,event(4,plate='1144'));assert bad.vehicle_id is None

def test_expired_watchlist_and_non_watchlisted(database):
    with database.begin() as s:
        watch(s,until=T-1);record_observation(s,event(1));record_observation(s,event(2,plate='MH04CD8877'))
        assert s.scalar(select(func.count()).select_from(Alert))==0

def test_out_of_order_and_attribute_conflicts(database):
    with database.begin() as s:
        record_observation(s,event(1,cam='C04',at=1440))
        ok,_=record_observation(s,event(2,cam='C01',at=0));assert ok.status=='accepted'
        bad,_=record_observation(s,event(3,cam='C01',at=1439));assert bad.status=='conflict'
        category={**event(4,at=2000),'vehicle_type':'bus'};bad,_=record_observation(s,category);assert bad.status=='conflict'

def test_traffic_journeys_buckets_and_congestion(database):
    with database.begin() as s:
        for i,plate in enumerate(['DL01AB1234','MH04CD8877','KA05MN2345']):
            record_observation(s,event(i*2,plate,at=i*2));record_observation(s,event(i*2+1,plate,cam='C02',at=600+i*2))
        record_observation(s,event(99,None,at=50))
        d=traffic_analytics(s,'run',T-1,T+700)
        assert d['passages']==7 and d['unreadable']==1
        assert d['od']==[{'from':'C01','to':'C02','count':3}]
        corridor=d['corridors'][0];assert corridor['median_seconds']==600 and corridor['samples']==3 and corridor['congestion']
        assert corridor['estimated_kmh']==9 and sum(x['count'] for x in d['buckets'])==7

def test_repeat_movement_rule(database):
    with database.begin() as s:
        for n,cam in enumerate(['C01','C02','C01','C02']):record_observation(s,event(n,cam=cam,at=n*300))
        assert s.scalar(select(Alert)).match_method=='rule'

def test_reset_preserves_stored_history(database):
    with database.begin() as s:
        obs,_=record_observation(s,event(1));original_id=obs.id;vehicle_id=obs.vehicle_id
        seed(s,reset=True)
        assert not s.get(DemoRun,'run').active
        assert s.get(Observation,original_id) and vehicle_dict(s,s.get(Vehicle,vehicle_id),'run')['sightings']==1
        assert get_run(s).id!='run'

def login(client,role='admin'):
    r=client.post('/api/v1/auth/login',json={'username':role,'password':os.environ['SYLRAK_'+role.upper()+'_PASSWORD']});assert r.status_code==200

def test_sessions_roles_csrf_upload_validation(database):
    client=TestClient(main.app)
    assert client.get('/api/v1/observations').status_code==401
    login(client,'operator')
    assert client.post('/api/v1/demo',json={'action':'reset'}).status_code==403
    assert client.get('/api/v1/audit').status_code==403
    assert client.post('/api/v1/observations',json=event(1)).status_code==403
    assert client.post('/api/v1/auth/logout',headers={'Origin':'https://example.net'}).status_code==403
    assert client.post('/api/v1/inference/jobs',files={'file':('bad.jpg',b'not an image','image/jpeg')}).status_code==422
    assert client.post('/api/v1/inference/jobs',files={'file':('big.jpg',b'x'*(10*1024*1024+1),'image/jpeg')}).status_code==413
    assert client.post('/api/v1/inference/jobs',data={'sample_id':'sample-027','camera_id':'C12'}).status_code==409

def test_filters_review_and_immutable_ocr(database):
    with database.begin() as s:
        watch(s);first,_=record_observation(s,event(1,details={'make_model':'Honda City','size_class':'mid-size','body_style':'sedan'}));fuzzy,_=record_observation(s,event(2,plate='DL01AB1235',confidence=.7));s.flush();a=s.scalar(select(Association).where(Association.observation_id==fuzzy.id));aid=a.id
    client=TestClient(main.app);login(client)
    r=client.get('/api/v1/observations',params={'plate':'dl 01-ab1234','camera':'C01','status':'accepted','alert_status':'open'}).json();assert r['total']==1
    described=client.get('/api/v1/observations',params={'vehicle_type':'car','color':'unknown','size_class':'mid-size','make_model':'honda'}).json();assert described['total']==1
    assert client.patch('/api/v1/associations/'+aid,json={'status':'rejected','reason':'Different number on the evidence'}).status_code==200
    with database() as s:
        assert s.get(Observation,fuzzy.id).raw_plate=='DL01AB1235'
        assert s.get(Observation,fuzzy.id).vehicle_id is None
        assert s.scalar(select(Alert).where(Alert.match_method=='possible')).status=='dismissed'
        assert s.scalar(select(func.count()).select_from(Audit))>=3

def test_stream_resume_only_emits_new_committed_events(database,monkeypatch):
    with database.begin() as s:emit(s,'first');s.flush();cursor=s.scalar(select(StreamEvent.id));emit(s,'second')
    class Request:
        headers={'last-event-id':str(cursor)}
        async def is_disconnected(self):return False
    monkeypatch.setattr(main,'current_user',lambda r:{'id':'operator'})
    async def run():
        response=await main.events(Request(),0,{'id':'operator'})
        message=await anext(response.body_iterator);assert 'second' in message and 'first' not in message
        await response.body_iterator.aclose()
    asyncio.run(run())

def test_failed_inference_is_actionable(database,monkeypatch):
    from backend import inference
    def fail(path):raise RuntimeError('Test decoder failure')
    monkeypatch.setattr(inference,'infer_image',fail);monkeypatch.setattr(main,'pool',None)
    with database.begin() as s:s.add(Job(id='badjob',input_path='bad.jpg',camera_id='C01',run_id='run'))
    asyncio.run(main.process_job('badjob'))
    with database() as s:assert s.get(Job,'badjob').status=='failed' and 'decoder' in s.get(Job,'badjob').error

def test_retention_preserves_shared_original(database):
    original=main.EVIDENCE/'same.jpg';original.write_bytes(b'test')
    with database.begin() as s:
        old=Evidence(original_path=str(original),sha256='a',source='test',license='test',width=1,height=1,created_at=0)
        live=Evidence(original_path=str(original),sha256='a',source='test',license='test',width=1,height=1)
        s.add_all([old,live]);s.flush();old_id=old.id;main.purge_expired(s)
        assert s.get(Evidence,old_id) is None and original.exists()

def test_duplicate_frames_cannot_raise_confidence():
    reading={'frame_sha256':'same','raw_plate':'DL01AB1234'}
    assert fuse_readings([reading]*5)['distinct_frames']==1

def test_overlapping_vehicle_regions_count_plate_once():
    a={'vehicle_box':[0,0,500,500],'plate_box':[100,100,200,150],'plate_confidence':.9}
    b={'vehicle_box':[20,0,500,500],'plate_box':[102,101,200,150],'plate_confidence':.8}
    assert len(deduplicate_detections([a,b]))==1
