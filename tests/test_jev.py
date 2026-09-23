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
    monkeypatch.setattr(jev,'classify',lambda text,key:(calls.append(text) or reply()))
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
    monkeypatch.setattr(jev,'classify',lambda text,key:(calls.append(text) or reply()))
    with client_for(database) as c:
        assert c.post('/api/v1/jev/describe',json={'text':'white sedan'}).status_code==200
        monkeypatch.setattr(jev,'DAILY_CALLS',1)
        assert c.post('/api/v1/jev/describe',json={'text':'black sedan'}).status_code==429
        monkeypatch.setattr(jev,'key',lambda:'')
        assert c.post('/api/v1/jev/describe',json={'text':'white sedan'}).json()['cached']
        assert len(calls)==1
