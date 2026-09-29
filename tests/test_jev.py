import httpx
from backend import jev
from test_extensions import client_for

def configure(monkeypatch,tmp_path):
    monkeypatch.setattr(jev,'LEDGER',tmp_path/'usage.db')
    monkeypatch.setattr(jev,'key',lambda:'test-only-secret')

def reply():
    return {'answers':{'color_white':{'choice':'yes','confidence':.98},
            'roof_color':{'choice':'2','confidence':.95},
            'vehicle_type':{'choice':'0','confidence':.95},
            'color_red':{'choice':'yes','confidence':.2}},
            'provider_metadata':{'gateway':{'cost':'.00005'}}}

def test_explicit_cached_request_budget_and_no_identity_changes(database,monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);calls=[]
    monkeypatch.setattr(jev,'classify',lambda text,key,*_:(calls.append(text) or reply()))
    with client_for(database) as c:
        assert c.get('/api/v1/jev/status').json()['requests']==0 and not calls
        r=c.post('/api/v1/jev/describe',json={'text':'white car with black roof'}).json()
        assert r['filters']['colors']==['white'] and r['filters']['regions']=={'roof':'black'}
        assert c.post('/api/v1/jev/describe',json={'text':'WHITE car with black roof'}).json()['cached']
        assert len(calls)==1
        monkeypatch.setattr(jev,'MAX_CALLS',1)
        assert c.post('/api/v1/jev/describe',json={'text':'another white car'}).status_code==429
        assert c.post('/api/v1/jev/describe',json={'text':'white car with black roof'}).status_code==200
        assert len(calls)==1

def test_failure_is_reserved_no_retry_no_secret(database,monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);calls=[]
    def fail(*args):
        calls.append(True);raise httpx.ConnectError('test-only-secret')
    monkeypatch.setattr(jev,'classify',fail)
    with client_for(database) as c:
        r=c.post('/api/v1/jev/describe',json={'text':'covered car'})
        assert r.status_code==503 and 'test-only-secret' not in r.text
        assert c.post('/api/v1/jev/describe',json={'text':'covered car'}).status_code==409
        assert c.get('/api/v1/jev/status').json()['requests']==1 and len(calls)==1

def test_unknown_and_malicious_response_not_applied():
    data=reply();data['answers']['vehicle_type']={'choice':'stolen','confidence':1}
    data['answers']['visibility']={'choice':'2','confidence':1}
    result=jev.safe_result(data)['filters']
    assert 'vehicle_type' not in result and 'regions' not in result

def test_daily_budget_and_cache_survive_reopened_ledger(database,monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);calls=[]
    monkeypatch.setattr(jev,'classify',lambda text,key,*_:(calls.append(text) or reply()))
    with client_for(database) as c:
        assert c.post('/api/v1/jev/describe',json={'text':'white sedan'}).status_code==200
        monkeypatch.setattr(jev,'DAILY_CALLS',1)
        assert c.post('/api/v1/jev/describe',json={'text':'black sedan'}).status_code==429
        monkeypatch.setattr(jev,'key',lambda:'')
        assert c.post('/api/v1/jev/describe',json={'text':'white sedan'}).json()['cached']
        assert len(calls)==1

def vehicle_reply():
    choose=lambda field,value,confidence=.95:{'choice':str(jev.VEHICLE_FIELDS[field][1].index(value)),'confidence':confidence}
    return {'answers':{'vehicle_type':choose('vehicle_type','car'),'color':choose('color','white'),
            'make_model':choose('make_model','Honda City'),'feature_type':choose('feature_type','sticker'),
            'feature_part':choose('feature_part','rear glass'),'region':choose('region','east-delhi'),
            'time_window':choose('time_window',60),'size_class':choose('size_class','large',.3)}}

def test_vehicle_description_maps_to_investigation_filters(database,monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);calls=[]
    monkeypatch.setattr(jev,'classify',lambda text,key,questions:(calls.append(questions) or vehicle_reply()))
    with client_for(database) as c:
        text='White Honda City with a sticker on the back glass, seen near Laxmi Nagar in the last hour'
        r=c.post('/api/v1/jev/describe-vehicle',json={'text':text}).json()
        assert r['filters']=={'vehicle_type':'car','color':'white','make_model':'Honda City','feature_type':'sticker',
                              'feature_part':'rear glass','region':'east-delhi','time_window':60}
        assert r['summary']==['white','car','Honda City','sticker on rear glass','East Delhi · Vikas Marg & Akshardham','last hour']
        assert calls[0] is jev.VEHICLE_QUESTIONS and not r['cached']
        # Cached separately from the appearance panel, but on the same credit ledger.
        assert c.post('/api/v1/jev/describe-vehicle',json={'text':text.upper()}).json()['cached']
        assert c.get('/api/v1/jev/status').json()['requests']==1 and len(calls)==1

def test_vehicle_description_rejects_unlisted_and_orphan_answers():
    data=vehicle_reply()
    data['answers']['color']={'choice':'99','confidence':1}
    data['answers']['feature_type']={'choice':'unknown','confidence':1}
    data['answers']['region']='east-delhi'
    filters=jev.vehicle_result(data)['filters']
    assert 'color' not in filters and 'region' not in filters and 'size_class' not in filters
    assert 'feature_type' not in filters and 'feature_part' not in filters
