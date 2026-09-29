from backend import db
from backend.marks import detectability, pixels, mark_fixtures
from backend.seed import appearance_fixtures
from backend.config import SCENARIO_START
from test_extensions import client_for, observation, OP

def test_detectability_follows_camera_resolution():
    assert detectability('decal / wrap',80)=='reliable'
    assert detectability('broken part',20)=='mostly'
    assert detectability('sticker',10)=='angle-dependent'
    assert detectability('glass damage',40)=='glare-limited'
    assert detectability('glass damage',1)=='close-up only'
    assert detectability('sticker',None)=='unknown'
    assert pixels(10)==29 and pixels(None) is None

def test_log_search_and_index_marks(database):
    with database.begin() as s:
        car=observation(s,'car',plate='DL8CAF2041').id
        other=observation(s,'other',plate='HR26DQ9021',camera='C02').id
    with client_for(database,OP) as c:
        first=c.post(f'/api/v1/observations/{car}/marks',json={'category':'sticker','part':'rear glass','label':'  Ganesh sticker ','size_cm':10})
        assert first.status_code==200
        mark=first.json()
        assert mark['label']=='Ganesh sticker' and mark['detectability']=='angle-dependent' and mark['status']=='confirmed'
        assert mark['vehicle_id'] and mark['plate']=='DL8CAF2041' and mark['pixels']==29
        duplicate=c.post(f'/api/v1/observations/{car}/marks',json={'category':'sticker','part':'rear glass','label':'ganesh  STICKER'})
        assert duplicate.status_code==409
        c.post(f'/api/v1/observations/{other}/marks',json={'category':'glass damage','part':'windshield','label':'Windshield chip','size_cm':1,'origin':'model suggestion'})
        assert c.post('/api/v1/observations/missing/marks',json={'category':'dent','part':'bonnet','label':'Dent'}).status_code==404
        assert c.post(f'/api/v1/observations/{car}/marks',json={'category':'graffiti','part':'bonnet','label':'Tag'}).status_code==422

        by_label=c.get('/api/v1/marks/search',params={'q':'GANESH'}).json()
        assert by_label['total']==1 and by_label['items'][0]['observation']['camera']['id']=='C01'
        by_part=c.get('/api/v1/marks/search',params={'part':'windshield'}).json()
        assert by_part['total']==1 and by_part['items'][0]['status']=='suggested'
        assert c.get('/api/v1/marks/search',params={'camera_id':'C02'}).json()['total']==1
        assert c.get('/api/v1/marks/search',params={'status':'confirmed'}).json()['total']==1

        index=c.get('/api/v1/marks/index').json()
        assert index['total']==2 and index['vehicles']==2
        assert index['category']=={'sticker':1,'glass damage':1}
        assert index['detectability']['close-up only']==1

        chip=by_part['items'][0]['id']
        assert c.patch('/api/v1/marks/'+chip,json={'status':'rejected','reason':'x'}).status_code==422
        rejected=c.patch('/api/v1/marks/'+chip,json={'status':'rejected','reason':'Reflection, not a chip.'}).json()
        assert [h['action'] for h in rejected['history']]==['logged','rejected']
        assert c.get('/api/v1/marks/index').json()['total']==1
        assert c.get('/api/v1/marks/search',params={'status':'rejected'}).json()['total']==1

        history=c.get('/api/v1/vehicles/'+mark['vehicle_id']+'/marks').json()
        assert [m['label'] for m in history]==['Ganesh sticker']
        assert c.get(f'/api/v1/observations/{other}/marks').json()[0]['status']=='rejected'
    with database() as s:
        assert s.query(db.Audit).filter(db.Audit.action=='mark.log').count()==2

def test_fixtures_are_idempotent_and_keep_unplated_sightings(database):
    with database.begin() as s:
        run=s.get(db.DemoRun,'run');appearance_fixtures(s,run);mark_fixtures(s,run)
    with database() as s:
        marks=s.query(db.VehicleMark).all()
        labels={m.label:m for m in marks}
        assert len(marks)==len(labels)
        assert labels['Red door panel wrap'].detectability=='reliable' and labels['Red door panel wrap'].vehicle_id
        assert labels['Cab operator decal on rear doors'].vehicle_id is None
    with client_for(database,OP) as c:
        index=c.get('/api/v1/marks/index').json()
        assert index['unidentified_sightings']>=2
        assert c.get('/api/v1/marks/search',params={'q':'cab operator'}).json()['total']==1

def test_description_search_filters_by_logged_features(database):
    with database.begin() as s:
        first=observation(s,'a1',plate='DL8CAF2041',camera='C01').id
        observation(s,'a2',plate='DL8CAF2041',camera='C02',at=SCENARIO_START+300)
        observation(s,'b1',plate='HR26DQ9021',camera='C03')
        unplated=observation(s,'u1',plate=None,camera='C04').id
    with client_for(database,OP) as c:
        c.post(f'/api/v1/observations/{first}/marks',json={'category':'sticker','part':'rear glass','label':'Ganesh sticker','size_cm':10})
        c.post(f'/api/v1/observations/{unplated}/marks',json={'category':'dent','part':'bonnet','label':'Bonnet dent','size_cm':30})
        def search(**params):return c.get('/api/v1/observations',params={'run_id':'','include_features':'true',**params}).json()
        by_type=search(feature_type='sticker')
        # Every sighting of the vehicle matches, including cameras where the sticker was not logged.
        assert by_type['total']==2 and {o['camera_id'] for o in by_type['items']}=={'C01','C02'}
        assert all(o['features'][0]['label']=='Ganesh sticker' for o in by_type['items'])
        assert search(feature_part='rear glass',color='white')['total']==2
        assert search(feature_type='sticker')['items'][0]['features'][0]['category']=='sticker'
        assert search(feature='GANESH')['total']==2
        assert search(feature_type='sticker',feature_part='bonnet')['total']==0
        dent=search(feature='bonnet dent')
        assert dent['total']==1 and dent['items'][0]['id']==unplated
        assert 'features' not in c.get('/api/v1/observations').json()['items'][0]
