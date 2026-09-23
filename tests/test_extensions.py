import time
from contextlib import contextmanager
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from backend import main,db,extensions
from backend.service import record_observation,emit
from backend.config import SCENARIO_START
from backend.seed import appearance_fixtures

ADMIN={'id':'admin','role':'admin','name':'Admin'}
OP={'id':'operator','role':'operator','name':'Operator'}

def test_appearance_watch_reactivation_and_stop(database):
    with client_for(database) as c:
        case=c.post('/api/v1/cases',json={'title':'Distinctive roof enquiry'}).json()
        body={'criteria':{'camera_ids':['C01'],'from_time':SCENARIO_START-60,
              'to_time':SCENARIO_START+600,'features':['roof rack']},'hours':1}
        first=c.post('/api/v1/cases/'+case['id']+'/watch',json=body)
        assert first.status_code==200
        again=c.post('/api/v1/cases/'+case['id']+'/watch',json=body)
        assert again.json()['id']==first.json()['id']
        stop=c.delete('/api/v1/cases/'+case['id']+'/watch/'+first.json()['id'])
        assert stop.status_code==200 and not stop.json()['active']
        detail=c.get('/api/v1/cases/'+case['id']).json()
        assert len(detail['watches'])==1

@contextmanager
def client_for(database,user=ADMIN):
    main.app.dependency_overrides[main.current_user]=lambda:user
    main.app.dependency_overrides[main.admin_user]=lambda:user if user['role']=='admin' else main.admin_user(None)
    client=TestClient(main.app)
    try:yield client
    finally:client.close();main.app.dependency_overrides.clear()

def observation(s,key='1',plate='DL8CAF2041',camera='C01',at=None):
    return record_observation(s,dict(event_key=key,track_id=key,camera_id=camera,observed_at=at or SCENARIO_START,run_id='run',raw_plate=plate,ocr_confidence=.98,vehicle_confidence=.95,plate_confidence=.97,vehicle_type='car',color='white',source_kind='synthetic',details={}))[0]

def watch(s,plate='DL8CAF2041',priority='critical'):
    w=db.Watchlist(plate=plate,category='stolen',reason='Demonstration only',reference=plate,priority=priority);s.add(w);s.flush();return w

def test_priority_and_vehicle_scoped_controls(database):
    with database.begin() as s:
        watch(s);watch(s,'DL4CAB2211','high');observation(s);observation(s,'2','DL4CAB2211',at=SCENARIO_START+300)
    with client_for(database) as c:
        assert [a['priority'] for a in c.get('/api/v1/alerts').json()]==['critical','high']
        body={'subject':'plate:DL8CAF2041','action':'mute','minutes':15}
        assert c.post('/api/v1/notification-preferences',json=body).json()['muted']
        assert len(c.get('/api/v1/alerts').json())==1
        muted=c.get('/api/v1/alerts?status=muted').json();assert len(muted)==1 and muted[0]['priority']=='critical'
        c.post('/api/v1/notification-preferences',json={**body,'action':'stop'})
        assert len(c.get('/api/v1/alerts?status=dismissed').json())==1
        with database.begin() as s:observation(s,'3',camera='C02',at=SCENARIO_START+600)
        assert len(c.get('/api/v1/alerts').json())==1
        assert len(c.get('/api/v1/alerts?status=muted').json())==1
    main.app.dependency_overrides.clear()

def test_notification_cursor_dedup_expiry_and_priority(database):
    with client_for(database) as c:
        assert c.post('/api/v1/notifications/poll').json()['items']==[]
        with database.begin() as s:watch(s);observation(s)
        assert len(c.post('/api/v1/notifications/poll').json()['items'])==1
        assert c.post('/api/v1/notifications/poll').json()['items']==[]
        with database.begin() as s:observation(s,'later',camera='C02',at=SCENARIO_START+600)
        assert c.post('/api/v1/notifications/poll').json()['items']==[]
        c.post('/api/v1/notification-preferences',json={'subject':'plate:DL8CAF2041','action':'mute','minutes':15})
        with database.begin() as s:
            a=s.scalar(select(db.Alert));a.priority='high';s.get(db.NotificationState,'admin').details={}
            emit(s,'alert.updated',{'id':a.id})
        assert c.post('/api/v1/notifications/poll').json()['items']==[]
        with database.begin() as s:
            p=s.scalar(select(db.NotificationPreference));p.until=time.time()-1
        # Expiry alone doesn't replay suppressed events.
        assert c.post('/api/v1/notifications/poll').json()['items']==[]
        with database.begin() as s:
            a=s.scalar(select(db.Alert));emit(s,'alert.updated',{'id':a.id})
        assert len(c.post('/api/v1/notifications/poll').json()['items'])==1
        with database.begin() as s:
            a=s.scalar(select(db.Alert));a.priority='critical';emit(s,'alert.updated',{'id':a.id})
        assert len(c.post('/api/v1/notifications/poll').json()['items'])==1
    main.app.dependency_overrides.clear()

def test_registration_is_independent_and_unknown_is_not_unregistered(database):
    with client_for(database) as c:
        r=c.get('/api/v1/registrations/dl-10-cz-7788').json()
        assert r['status']=='demo_found' and r['record']['model']=='Dzire' and not r['live_connected']
        r=c.get('/api/v1/registrations/DL99ZZ9999').json()
        assert r['record'] is None and r['status']=='unavailable' and 'unregistered' not in r['message'].lower()
        with database() as s:
            assert s.scalar(select(func.count()).select_from(db.Observation))==0
            assert s.scalar(select(func.count()).select_from(db.Vehicle))==0
            assert s.scalar(select(func.count()).select_from(db.Alert))==0
    main.app.dependency_overrides.clear()

def test_common_cars_occlusion_and_reversible_case_reviews(database):
    with database.begin() as s:appearance_fixtures(s,s.get(db.DemoRun,'run'))
    with client_for(database) as c:
        result=c.post('/api/v1/search/candidates',json={'make_model':'Dzire','colors':['white'],'plate_visibility':'visibly absent','include_unknown':False}).json()
        candidates=[x for x in result['items'] if not x['explanation']['conflicts']]
        assert len(candidates)==5
        assert len({x['id'] for x in candidates})==5
        assert all(x['observation']['vehicle_id'] is None for x in candidates)
        covered=c.post('/api/v1/search/candidates',json={'visibility':'heavily obscured','regions':{'body':'silver'}}).json()['items']
        blue=[x for x in covered if x['observation']['details'].get('appearance',{}).get('visibility')=='heavily obscured']
        assert blue and all('body silver' in x['explanation']['unknown'] for x in blue)
        ids=[x['observation']['id'] for x in candidates[:2]]
        case=c.post('/api/v1/cases',json={'title':'Common white Dzires','observation_ids':ids}).json()
        detail=c.get('/api/v1/cases/'+case['id']).json();link=detail['links'][0]
        path=f"/api/v1/cases/{case['id']}/links/{link['id']}"
        for status in ['accepted','rejected','proposed']:
            assert c.patch(path,json={'status':status,'reason':'Reviewed visible evidence'}).json()['status']==status
        detail=c.get('/api/v1/cases/'+case['id']).json()
        assert len(detail['links'][0]['history'])==4
        with database() as s:
            assert s.get(db.Observation,ids[0]).vehicle_id is None
            assert s.get(db.Observation,ids[0]).status=='unresolved'
        assert c.post('/api/v1/cases/'+case['id']+'/watch',json={'criteria':{'colors':['white']}}).status_code==422
    main.app.dependency_overrides.clear()

def test_operator_cannot_globally_suppress_and_personal_mute_isolated(database):
    with database.begin() as s:watch(s);observation(s)
    with client_for(database,OP) as c:
        assert c.post('/api/v1/notification-preferences',json={'subject':'plate:DL8CAF2041','action':'stop'}).status_code==403
        assert c.post('/api/v1/notification-preferences',json={'subject':'plate:DL8CAF2041','action':'mute'}).status_code==200
    main.app.dependency_overrides.clear()
    with client_for(database) as c:assert len(c.get('/api/v1/alerts').json())==1
    main.app.dependency_overrides.clear()
