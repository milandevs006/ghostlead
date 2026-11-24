"""GhostLead: local-first lead integrity workspace. No seed data or outbound scans."""
import csv, hashlib, io, os, secrets, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Text, ForeignKey, UniqueConstraint, select, func, event, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DB_URL = os.getenv('GHOSTLEAD_DATABASE_URL', f'sqlite:///{DATA / "ghostlead.db"}')
engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {})
if DB_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_fk(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=5000')
class Base(DeclarativeBase): pass
class Owner(Base):
    __tablename__='owners'
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(String(254), unique=True)
    password_hash: Mapped[str]=mapped_column(Text)
    workspace: Mapped[str]=mapped_column(String(100))
class LoginSession(Base):
    __tablename__='sessions'
    token: Mapped[str]=mapped_column(String(64), primary_key=True)
    expires: Mapped[int]=mapped_column(Integer)
class Site(Base):
    __tablename__='sites'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    url: Mapped[str]=mapped_column(String(2048), unique=True)
    created_at: Mapped[str]=mapped_column(String(32))
class Monitor(Base):
    __tablename__='monitors'
    __table_args__=(UniqueConstraint('site_id','name'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    site_id: Mapped[int]=mapped_column(ForeignKey('sites.id',ondelete='CASCADE'))
    name: Mapped[str]=mapped_column(String(120))
    kind: Mapped[str]=mapped_column(String(50))
class Run(Base):
    __tablename__='runs'
    __table_args__=(UniqueConstraint('monitor_id','observed_at'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    monitor_id: Mapped[int]=mapped_column(ForeignKey('monitors.id',ondelete='CASCADE'))
    observed_at: Mapped[str]=mapped_column(String(32))
    status: Mapped[str]=mapped_column(String(20))
    latency_ms: Mapped[int|None]=mapped_column(Integer, nullable=True)
    detail: Mapped[str]=mapped_column(Text,default='')
class LeadEvent(Base):
    __tablename__='lead_events'
    __table_args__=(UniqueConstraint('site_id','event_key','stage'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    site_id: Mapped[int]=mapped_column(ForeignKey('sites.id',ondelete='CASCADE'))
    event_key: Mapped[str]=mapped_column(String(150))
    stage: Mapped[str]=mapped_column(String(20))
    observed_at: Mapped[str]=mapped_column(String(32))
class ImportLog(Base):
    __tablename__='imports'
    id: Mapped[int]=mapped_column(primary_key=True)
    kind: Mapped[str]=mapped_column(String(40))
    filename: Mapped[str]=mapped_column(String(250))
    rows: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[str]=mapped_column(String(32))
Base.metadata.create_all(engine)
app=FastAPI(title='GhostLead',version='0.1.0',docs_url=None,redoc_url=None,openapi_url=None)
app.mount('/static',StaticFiles(directory=ROOT/'app/static'),name='static')
ph=PasswordHasher()
COOKIE='ghostlead_session'
SECURE=os.getenv('GHOSTLEAD_SECURE_COOKIE','0')=='1'

def now(): return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def timestamp(v):
    try:
        d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        if d.tzinfo is None: raise ValueError()
        return d.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    except (ValueError,TypeError,OverflowError): raise ValueError('Use an ISO 8601 date/time with timezone, e.g. YYYY-MM-DDTHH:MM:SSZ.')
def clean(v,maxlen,label):
    v=str(v or '').strip()
    if not v or len(v)>maxlen: raise ValueError(f'{label} must be 1–{maxlen} characters.')
    return v
def url(v):
    v=clean(v,2048,'Website URL')
    try:
        p=urlsplit(v)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.fragment or any(c.isspace() for c in v): raise ValueError()
        _=p.port
    except ValueError: raise ValueError('Enter a valid HTTP(S) URL without credentials or fragments.')
    return v.rstrip('/')
def db():
    with Session(engine) as s: yield s
def digest(t): return hashlib.sha256(t.encode()).hexdigest()
def logged(r:Request,s:Session):
    t=r.cookies.get(COOKIE,'')
    if not t:return False
    x=s.get(LoginSession,digest(t)); return bool(x and x.expires>time.time())
def auth(r:Request,s:Session=Depends(db)):
    if not logged(r,s): raise HTTPException(401,'Sign in to continue.')
    return s

def login_cookie(response,s):
    t=secrets.token_urlsafe(32); s.execute(delete(LoginSession).where(LoginSession.expires<=int(time.time())))
    s.add(LoginSession(token=digest(t),expires=int(time.time())+86400*7)); s.commit()
    response.set_cookie(COOKIE,t,httponly=True,samesite='strict',secure=SECURE,max_age=86400*7,path='/')
@app.middleware('http')
async def guard(r:Request,call_next):
    # Custom same-origin header prevents cross-site form submissions; no CORS enabled.
    if r.method not in ('GET','HEAD','OPTIONS'):
        if r.headers.get('x-ghostlead-request')!='1' or r.headers.get('sec-fetch-site')=='cross-site': return JSONResponse({'detail':'Request origin not allowed.'},403)
        if int(r.headers.get('content-length','0') or 0)>2_100_000: return JSONResponse({'detail':'Request exceeds 2 MB.'},413)
    res=await call_next(r)
    res.headers['X-Content-Type-Options']='nosniff'; res.headers['X-Frame-Options']='DENY'; res.headers['Referrer-Policy']='no-referrer'
    res.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if r.url.path.startswith('/api') or r.url.path=='/': res.headers['Cache-Control']='no-store'
    return res
@app.exception_handler(ValueError)
async def bad_value(r,e):return JSONResponse({'detail':str(e)},400)
@app.exception_handler(IntegrityError)
async def duplicate(r,e):return JSONResponse({'detail':'Duplicate record or invalid reference. No changes saved.'},409)
@app.get('/')
def index():return FileResponse(ROOT/'app/static/index.html')
@app.get('/api/session')
def session_state(r:Request,s:Session=Depends(db)):
    owner=s.get(Owner,1); ok=bool(owner and logged(r,s))
    return {'configured':bool(owner),'authenticated':ok,'workspace':owner.workspace if ok else None,'email':owner.email if ok else None}
class Credentials(BaseModel):
    email:str=Field(max_length=254); password:str=Field(max_length=256); workspace:str=''
@app.post('/api/setup')
def setup(p:Credentials,response:Response,s:Session=Depends(db)):
    if s.get(Owner,1):raise HTTPException(409,'Workspace already configured.')
    email=clean(p.email,254,'Email').lower()
    if '@' not in email or email.startswith('@') or email.endswith('@'):raise ValueError('Enter a valid email address.')
    if len(p.password)<12:raise ValueError('Use a password of at least 12 characters.')
    s.add(Owner(id=1,email=email,password_hash=ph.hash(p.password),workspace=clean(p.workspace,100,'Workspace name'))); s.commit(); login_cookie(response,s);return {'ok':True}
# Simple local-process throttle. Public production requires stronger distributed rate limiting.
ATTEMPTS={}
@app.post('/api/login')
def login(p:Credentials,r:Request,response:Response,s:Session=Depends(db)):
    ip=r.client.host if r.client else 'local'; t=time.time(); tries=[x for x in ATTEMPTS.get(ip,[]) if t-x<300]
    if len(tries)>=8:raise HTTPException(429,'Too many attempts. Try again in five minutes.')
    owner=s.get(Owner,1); ok=False
    if owner and owner.email==p.email.strip().lower():
        try:ok=ph.verify(owner.password_hash,p.password)
        except (VerificationError,InvalidHashError):pass
    if not ok:ATTEMPTS[ip]=tries+[t];raise HTTPException(401,'Invalid email or password.')
    ATTEMPTS.pop(ip,None);login_cookie(response,s);return {'ok':True}
@app.post('/api/logout')
def logout(r:Request,response:Response,s:Session=Depends(auth)):
    s.execute(delete(LoginSession).where(LoginSession.token==digest(r.cookies[COOKIE])));s.commit();response.delete_cookie(COOKIE,path='/');return {'ok':True}
KINDS=['Contact form','Booking flow','CRM delivery','Webhook','Website availability','Other']
STATUSES=['passed','failed','inconclusive']
HEADERS={'websites':['name','url'],'monitors':['website_url','name','kind'],'runs':['website_url','monitor_name','observed_at','status','latency_ms','detail'],'lead_events':['website_url','event_key','stage','observed_at']}
def get_site(s,v):
    x=s.scalar(select(Site).where(Site.url==url(v)))
    if not x:raise ValueError('Website does not exist. Add or import it first.')
    return x
def get_monitor(s,row):
    site=get_site(s,row.get('website_url'));x=s.scalar(select(Monitor).where(Monitor.site_id==site.id,Monitor.name==clean(row.get('monitor_name'),120,'Monitor name')))
    if not x:raise ValueError('Monitor does not exist. Add or import it first.')
    return x
def insert(s,kind,row):
    if kind=='websites':obj=Site(name=clean(row.get('name'),120,'Name'),url=url(row.get('url')),created_at=now())
    elif kind=='monitors':
        k=row.get('kind');
        if k not in KINDS:raise ValueError('Invalid monitor kind.')
        obj=Monitor(site_id=get_site(s,row.get('website_url')).id,name=clean(row.get('name'),120,'Monitor name'),kind=k)
    elif kind=='runs':
        status=row.get('status');
        if status not in STATUSES:raise ValueError('Status must be passed, failed or inconclusive.')
        latency=row.get('latency_ms');latency=int(latency) if latency not in (None,'') else None
        if latency is not None and not 0<=latency<=86400000:raise ValueError('Invalid latency in milliseconds.')
        detail=str(row.get('detail') or '')
        if len(detail)>2000:raise ValueError('Detail exceeds 2000 characters.')
        obj=Run(monitor_id=get_monitor(s,row).id,observed_at=timestamp(row.get('observed_at')),status=status,latency_ms=latency,detail=detail)
    elif kind=='lead_events':
        stage=row.get('stage');
        if stage not in ('source','destination'):raise ValueError('Stage must be source or destination.')
        obj=LeadEvent(site_id=get_site(s,row.get('website_url')).id,event_key=clean(row.get('event_key'),150,'Event key'),stage=stage,observed_at=timestamp(row.get('observed_at')))
    else:raise ValueError('Unknown record type.')
    s.add(obj);s.flush();return obj
@app.post('/api/records/{kind}')
def create_record(kind:str,row:dict,s:Session=Depends(auth)):
    obj=insert(s,kind,row);id=obj.id;s.commit();return {'id':id}
class CSVImport(BaseModel):
    filename:str=Field(max_length=250); content:str=Field(max_length=2_000_000)
@app.post('/api/import/{kind}')
def import_csv(kind:str,p:CSVImport,s:Session=Depends(auth)):
    if kind not in HEADERS:raise HTTPException(404,'Unknown import type.')
    reader=csv.DictReader(io.StringIO(p.content.lstrip('\ufeff')),strict=True)
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or set(reader.fieldnames)!=set(HEADERS[kind]):raise ValueError('CSV headers must match: '+', '.join(HEADERS[kind]))
    count=0
    try:
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise ValueError('Wrong number of fields.')
            if not any(v.strip() for v in row.values()):continue
            count+=1
            if count>10000:raise ValueError('Maximum 10,000 rows per import.')
            insert(s,kind,row)
        if not count:raise ValueError('File has no data rows.')
    except (ValueError,IntegrityError,csv.Error) as e:
        s.rollback();raise ValueError(f'CSV line {reader.line_num}: '+('Duplicate record or invalid reference.' if isinstance(e,IntegrityError) else str(e))+' Entire import rolled back.')
    s.add(ImportLog(kind=kind,filename=p.filename,rows=count,created_at=now()));s.commit();return {'rows':count}

def serialize(x):return {c.name:getattr(x,c.name) for c in x.__table__.columns}
@app.get('/api/workspace')
def workspace(s:Session=Depends(auth)):
    sites=[serialize(x) for x in s.scalars(select(Site).order_by(Site.id))]; monitors=[serialize(x) for x in s.scalars(select(Monitor).order_by(Monitor.id))]
    runs=[serialize(x) for x in s.scalars(select(Run).order_by(Run.observed_at.desc(),Run.id.desc()))]; events=[serialize(x) for x in s.scalars(select(LeadEvent).order_by(LeadEvent.observed_at.desc()))]
    imports=[serialize(x) for x in s.scalars(select(ImportLog).order_by(ImportLog.id.desc()))]
    return {'websites':sites,'monitors':monitors,'runs':runs,'lead_events':events,'imports':imports,'kinds':KINDS,'headers':HEADERS}
@app.delete('/api/records/{kind}/{id}')
def remove(kind:str,id:int,s:Session=Depends(auth)):
    model={'websites':Site,'monitors':Monitor,'runs':Run,'lead_events':LeadEvent}.get(kind)
    if not model:raise HTTPException(404,'Unknown record type.')
    obj=s.get(model,id)
    if not obj:raise HTTPException(404,'Record not found.')
    s.delete(obj);s.commit();return {'ok':True}

# Stage 2.3: user-authored workflow layouts, separate from observed events.
# Additive schema only; existing workspace tables are not changed or seeded.
from sqlalchemy import update
from pydantic import ConfigDict
from typing import Literal
import json

class JourneyLayout(Base):
    __tablename__ = 'journey_layouts'
    site_id: Mapped[int] = mapped_column(ForeignKey('sites.id', ondelete='CASCADE'), primary_key=True)
    graph_json: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[str] = mapped_column(String(32))

JourneyLayout.__table__.create(engine, checkfirst=True)

class JourneyNode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    kind: Literal['website','form','booking','webhook','crm','notification','other']
    label: str = Field(min_length=1, max_length=120)
    x: float = Field(ge=-100000, le=100000, allow_inf_nan=False)
    y: float = Field(ge=-100000, le=100000, allow_inf_nan=False)

class JourneyEdge(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)

class JourneyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=0, le=2147483646)
    nodes: list[JourneyNode] = Field(max_length=100)
    edges: list[JourneyEdge] = Field(max_length=300)

def journey_site(s, site_id):
    if not s.get(Site, site_id):
        raise HTTPException(404, 'Website not found.')

def journey_response(site_id, row):
    return {'site_id': site_id, 'revision': row.revision if row else 0,
            'updated_at': row.updated_at if row else None,
            **(json.loads(row.graph_json) if row else {'nodes': [], 'edges': []})}

@app.get('/api/journeys/{site_id}')
def get_journey(site_id: int, s: Session=Depends(auth)):
    journey_site(s, site_id)
    return journey_response(site_id, s.get(JourneyLayout, site_id))

@app.put('/api/journeys/{site_id}')
def save_journey(site_id: int, payload: JourneyInput, s: Session=Depends(auth)):
    journey_site(s, site_id)
    ids = {n.id for n in payload.nodes}
    if len(ids) != len(payload.nodes): raise ValueError('Duplicate node identifiers.')
    for node in payload.nodes:
        node.label = clean(node.label, 120, 'Node label')
    edge_ids, connections = set(), set()
    for edge in payload.edges:
        pair = (edge.source, edge.target)
        if edge.source not in ids or edge.target not in ids or edge.source == edge.target:
            raise ValueError('Each connection must link two different existing nodes.')
        if edge.id in edge_ids or pair in connections: raise ValueError('Duplicate connection.')
        edge_ids.add(edge.id); connections.add(pair)
    graph = json.dumps(payload.model_dump(include={'nodes','edges'}), ensure_ascii=False)
    stamp = now()
    values = dict(graph_json=graph, revision=payload.revision+1, updated_at=stamp)
    if payload.revision == 0:
        if s.get(JourneyLayout, site_id): raise HTTPException(409, 'Journey changed. Reload before saving.')
        s.add(JourneyLayout(site_id=site_id, **values))
        try: s.commit()
        except IntegrityError:
            s.rollback(); raise HTTPException(409, 'Journey changed or website removed. Reload before saving.')
    else:
        result = s.execute(update(JourneyLayout).where(JourneyLayout.site_id==site_id, JourneyLayout.revision==payload.revision).values(**values))
        if result.rowcount != 1:
            s.rollback(); raise HTTPException(409, 'Journey changed. Reload before saving.')
        s.commit()
    return {'site_id':site_id, 'revision':payload.revision+1, 'updated_at':stamp, **json.loads(graph)}
