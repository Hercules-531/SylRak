import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SYLRAK_RUNTIME']=tempfile.mkdtemp(prefix='sylrak-tests-')
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import db,auth,main
from backend.geo import CAMERAS
from backend.config import SCENARIO_START

@pytest.fixture
def database(tmp_path,monkeypatch):
    engine=create_engine('sqlite:///'+(tmp_path/'test.db').as_posix(),connect_args={'check_same_thread':False})
    db.Base.metadata.create_all(engine);session=sessionmaker(engine,expire_on_commit=False)
    for module in [db,main,auth]:monkeypatch.setattr(module,'Session',session)
    monkeypatch.setattr(main,'EVIDENCE',tmp_path/'evidence');(tmp_path/'evidence').mkdir()
    with session.begin() as s:
        for id,name,road,lat,lon,direction,status in CAMERAS:s.add(db.Camera(id=id,name=name,road=road,lat=lat,lon=lon,direction=direction,status=status))
        s.add(db.DemoRun(id='run',state={'clock':SCENARIO_START,'status':'idle','speed':12}));auth.init_users(s)
    yield session
    engine.dispose()
