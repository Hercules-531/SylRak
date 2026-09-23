from sqlalchemy import select,func
from backend import db
from backend.review_score import theft_review
from backend.config import SCENARIO_START
from test_extensions import observation,watch,client_for

def test_review_signals_are_explainable_and_read_only(database):
    with database.begin() as s:
        watch(s)
        sighting=observation(s)
        before=s.scalar(select(func.count()).select_from(db.Alert))
        result=theft_review(s,sighting)
        assert result['score']==70 and not result['calibrated']
        assert result['reasons'][0]['code']=='watchlist_exact'
        assert 'not a probability' in result['warning']
        assert s.scalar(select(func.count()).select_from(db.Alert))==before

def test_patterns_do_not_use_future_or_other_run_events(database):
    with database.begin() as s:
        rows=[observation(s,str(i),camera=c,at=SCENARIO_START+i*240) for i,c in enumerate(['C01','C02','C01','C02'])]
        assert theft_review(s,rows[0])['score']==0
        score=theft_review(s,rows[-1])
        assert score['score']==20 and score['accepted_history_count']==4
        rows[-1].run_id='different-run';s.flush()
        assert theft_review(s,rows[-1])['score']==0

def test_unreadable_is_not_absent_and_hidden_data_is_unknown(database):
    with database.begin() as s:
        o=observation(s,plate=None)
        o.details={'appearance':{'visibility':'unknown','plate_visibility':'unreadable'}}
        assert theft_review(s,o)['score'] is None
        o.details={'appearance':{'visibility':'heavily obscured','plate_visibility':'visibly absent'}}
        r=theft_review(s,o)
        assert r['score']==20 and r['accepted_history_count']==0

def test_expired_record_does_not_raise_review_score(database):
    with database.begin() as s:
        w=watch(s);w.valid_until=SCENARIO_START-1;o=observation(s)
        assert theft_review(s,o)['score']==0

def test_search_and_vehicle_detail_return_review_without_merging(database):
    with database.begin() as s:
        watch(s);o=observation(s);vid=o.vehicle_id
    with client_for(database) as c:
        r=c.get('/api/v1/observations?plate=DL8CAF2041&include_review=true').json()
        assert r['items'][0]['theft_review']['score']==70
        assert c.get('/api/v1/vehicles/'+vid).json()['theft_review']['score']==70
        candidates=c.post('/api/v1/search/candidates',json={'colors':['white']}).json()
        assert candidates['items'][0]['explanation']['match_score']==100
        assert candidates['items'][0]['theft_review']['experimental']
