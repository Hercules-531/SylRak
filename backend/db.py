import time, uuid
from sqlalchemy import create_engine, event, String, Float, Integer, Boolean, JSON, Index, ForeignKey, Text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DB_URL

def uid(): return uuid.uuid4().hex
class Base(DeclarativeBase): pass
engine = create_engine(DB_URL, connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def sqlite_pragmas(conn, _):
    conn.execute('PRAGMA journal_mode=WAL'); conn.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)

class SchemaVersion(Base):
    __tablename__='schema_versions'
    version: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[float] = mapped_column(default=time.time)
class Camera(Base):
    __tablename__='cameras'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    road: Mapped[str]
    lat: Mapped[float]
    lon: Mapped[float]
    direction: Mapped[str]
    status: Mapped[str] = mapped_column(default='online')
    source_type: Mapped[str] = mapped_column(default='simulated')
    heartbeat: Mapped[float] = mapped_column(default=time.time)
class Vehicle(Base):
    __tablename__='vehicles'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    plate: Mapped[str] = mapped_column(String, unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(default='unknown')
    color: Mapped[str] = mapped_column(default='unknown')
class Evidence(Base):
    __tablename__='evidence'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    original_path: Mapped[str]
    plate_path: Mapped[str|None]
    vehicle_path: Mapped[str|None]
    sha256: Mapped[str]
    source: Mapped[str]
    license: Mapped[str]
    sample_id: Mapped[str|None]
    width: Mapped[int]
    height: Mapped[int]
    models: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(default=time.time)
    bundled: Mapped[bool] = mapped_column(default=False)
class Observation(Base):
    __tablename__='observations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    event_key: Mapped[str] = mapped_column(String, unique=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey('cameras.id'))
    vehicle_id: Mapped[str|None] = mapped_column(ForeignKey('vehicles.id'), index=True)
    observed_at: Mapped[float] = mapped_column(index=True)
    ingested_at: Mapped[float] = mapped_column(default=time.time)
    run_id: Mapped[str] = mapped_column(index=True)
    track_id: Mapped[str]
    raw_plate: Mapped[str|None]
    plate: Mapped[str|None] = mapped_column(index=True)
    vehicle_type: Mapped[str] = mapped_column(default='unknown')
    color: Mapped[str] = mapped_column(default='unknown')
    ocr_confidence: Mapped[float|None]
    vehicle_confidence: Mapped[float|None]
    plate_confidence: Mapped[float|None]
    status: Mapped[str] = mapped_column(default='unresolved')
    source_kind: Mapped[str]
    evidence_id: Mapped[str|None] = mapped_column(ForeignKey('evidence.id'))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__=(Index('ix_observation_camera_time','camera_id','observed_at'), Index('ix_observation_plate_time','plate','observed_at'),Index('ix_observation_track','run_id','camera_id','track_id',unique=True))
class Association(Base):
    __tablename__='associations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'), unique=True)
    vehicle_id: Mapped[str|None] = mapped_column(ForeignKey('vehicles.id'))
    status: Mapped[str]
    score: Mapped[float|None]
    reason: Mapped[str]
    reviewed_by: Mapped[str|None]
class Watchlist(Base):
    __tablename__='watchlist'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    plate: Mapped[str] = mapped_column(index=True)
    category: Mapped[str]
    reason: Mapped[str]
    reference: Mapped[str]
    priority: Mapped[str] = mapped_column(default='critical')
    active: Mapped[bool] = mapped_column(default=True)
    valid_from: Mapped[float|None]
    valid_until: Mapped[float|None]
    created_at: Mapped[float] = mapped_column(default=time.time)
class Alert(Base):
    __tablename__='alerts'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    episode_key: Mapped[str] = mapped_column(String, unique=True)
    vehicle_id: Mapped[str|None] = mapped_column(ForeignKey('vehicles.id'))
    watchlist_id: Mapped[str|None] = mapped_column(ForeignKey('watchlist.id'))
    observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'))
    latest_observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'))
    run_id: Mapped[str]
    priority: Mapped[str]
    category: Mapped[str]
    reason: Mapped[str]
    match_method: Mapped[str]
    status: Mapped[str] = mapped_column(default='open')
    created_at: Mapped[float]
    updated_at: Mapped[float]
class DemoRun(Base):
    __tablename__='demo_runs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    active: Mapped[bool] = mapped_column(default=True,index=True)
    created_at: Mapped[float] = mapped_column(default=time.time)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
class Job(Base):
    __tablename__='jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    status: Mapped[str] = mapped_column(default='queued')
    input_path: Mapped[str]
    camera_id: Mapped[str]
    sample_id: Mapped[str|None]
    run_id: Mapped[str]
    created_at: Mapped[float] = mapped_column(default=time.time)
    result: Mapped[dict|None] = mapped_column(JSON)
    error: Mapped[str|None]
class User(Base):
    __tablename__='users'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    role: Mapped[str]
    password_hash: Mapped[str]
class LoginSession(Base):
    __tablename__='sessions'
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[float]
class Audit(Base):
    __tablename__='audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str]
    action: Mapped[str]
    target: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(default=time.time)
class StreamEvent(Base):
    __tablename__='stream_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(default=time.time)

class NotificationPreference(Base):
    __tablename__='notification_preferences'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str]  # '*' denotes administrator-controlled suppression.
    subject: Mapped[str]
    muted: Mapped[bool] = mapped_column(default=False)
    until: Mapped[float|None]
    __table_args__=(Index('ix_notification_subject','user_id','subject',unique=True),)

class NotificationState(Base):
    __tablename__='notification_state'
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    cursor: Mapped[int] = mapped_column(default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

class InvestigationCase(Base):
    __tablename__='investigation_cases'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(default='')
    created_by: Mapped[str]
    created_at: Mapped[float] = mapped_column(default=time.time)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)

class CaseLink(Base):
    __tablename__='case_links'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('investigation_cases.id'))
    observation_id: Mapped[str]  # May outlive retention; expired evidence is explicit.
    status: Mapped[str] = mapped_column(default='proposed')
    history: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__=(Index('ix_case_observation','case_id','observation_id',unique=True),)

class AppearanceWatch(Base):
    __tablename__='appearance_watches'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('investigation_cases.id'))
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(default=True)
    expires_at: Mapped[float]

class VehicleMark(Base):
    """One visible abnormal feature on one sighting, indexed for cross-camera search."""
    __tablename__='vehicle_marks'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'), index=True)
    vehicle_id: Mapped[str|None] = mapped_column(ForeignKey('vehicles.id'), index=True)
    run_id: Mapped[str] = mapped_column(index=True)
    category: Mapped[str]
    part: Mapped[str]
    label: Mapped[str]
    label_key: Mapped[str] = mapped_column(index=True)
    size_cm: Mapped[float|None]
    detectability: Mapped[str] = mapped_column(index=True)
    origin: Mapped[str]
    status: Mapped[str] = mapped_column(default='confirmed', index=True)
    notes: Mapped[str] = mapped_column(default='')
    created_by: Mapped[str]
    created_at: Mapped[float] = mapped_column(default=time.time)
    history: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__=(Index('ix_mark_category_part','category','part'),Index('ix_mark_observation_label','observation_id','label_key',unique=True))

def migrate():
    # Versioned, additive baseline; migrations run before serving requests.
    Base.metadata.create_all(engine)
    with Session.begin() as s:
        s.execute(insert(SchemaVersion).values(version=1,applied_at=time.time()).on_conflict_do_nothing())
        s.execute(insert(SchemaVersion).values(version=2,applied_at=time.time()).on_conflict_do_nothing())
        s.execute(insert(SchemaVersion).values(version=3,applied_at=time.time()).on_conflict_do_nothing())
    # Additive migration for existing prototype databases.
    with engine.begin() as c:
        c.exec_driver_sql('CREATE UNIQUE INDEX IF NOT EXISTS ix_observation_track ON observations (run_id,camera_id,track_id)')

def row_dict(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}
