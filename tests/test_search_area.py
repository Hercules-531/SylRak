from backend.config import SCENARIO_START
from backend.geo import REGIONS, CAMERAS
from test_extensions import client_for, observation, OP

def test_regions_cover_each_camera_once():
    assigned=[c for r in REGIONS for c in r['cameras']]
    assert sorted(assigned)==sorted(c[0] for c in CAMERAS)

def test_search_by_region_radius_and_time(database):
    with database.begin() as s:
        observation(s,'cp',plate='DL8CAF2041',camera='C01',at=SCENARIO_START-3600)
        observation(s,'cp-late',plate='DL8CAF2041',camera='C07',at=SCENARIO_START-60)
        observation(s,'ito',plate='DL8CAF2041',camera='C03',at=SCENARIO_START-600)
        observation(s,'east',plate='HR26DQ9021',camera='C09',at=SCENARIO_START-300)
    with client_for(database,OP) as c:
        def search(**params):return c.get('/api/v1/observations',params={'run_id':'',**params}).json()
        region=search(region='connaught-place')
        assert region['total']==2 and region['area_cameras']==['C01','C07']
        # Region and time window combine: only the late Connaught Place sighting remains.
        late=search(region='connaught-place',from_time=SCENARIO_START-900,to_time=SCENARIO_START)
        assert [o['camera_id'] for o in late['items']]==['C07']
        near=search(near='C02',radius_km=1.5)
        assert set(near['area_cameras'])>={'C01','C02','C03'} and 'C09' not in near['area_cameras']
        assert {o['camera_id'] for o in near['items']}=={'C01','C03','C07'} & set(near['area_cameras'])
        # A region intersected with a radius narrows further.
        both=search(region='mandi-house-ito',near='C02',radius_km=0.5)
        assert both['area_cameras']==['C02'] and both['total']==0
        assert search(region='east-delhi',plate='HR26')['total']==1
        assert search()['area_cameras'] is None
        assert c.get('/api/v1/observations',params={'region':'nowhere'}).status_code==422
        assert c.get('/api/v1/observations',params={'near':'C99'}).status_code==422
        assert c.get('/api/v1/observations',params={'near':'C01','radius_km':0}).status_code==422
        assert [r['id'] for r in c.get('/api/v1/regions').json()]==[r['id'] for r in REGIONS]
