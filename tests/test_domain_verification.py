"""Isolated test database; DNS responses are mocked; no external traffic."""
import importlib
import time
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('GHOSTLEAD_DATABASE_URL', 'sqlite:///'+str(tmp_path/'verification.db'))
    main=importlib.import_module('app.main')
    isolated=create_engine('sqlite:///'+str(tmp_path/'isolated.db'),connect_args={'check_same_thread':False})
    @event.listens_for(isolated,'connect')
    def fk(conn,_): conn.execute('PRAGMA foreign_keys=ON')
    main.Base.metadata.create_all(isolated)
    monkeypatch.setattr(main,'engine',isolated)
    with TestClient(main.app,headers={'X-GhostLead-Request':'1'}) as client:
        assert client.post('/api/setup',json={'email':'test@example.invalid','password':'isolated-test-password','workspace':'Isolated'}).status_code==200
        assert client.post('/api/records/websites',json={'name':'Fixture','url':'https://www.example.com/form'}).status_code==200
        site=client.get('/api/workspace').json()['websites'][0]
        yield main,client,site['id']
    isolated.dispose()


def test_dns_lifecycle(workspace,monkeypatch):
    main,c,i=workspace
    path=f'/api/verification/{i}'
    assert TestClient(main.app).get(path).status_code==401
    assert c.get(path).json()['status']=='unverified'
    assert c.get('/api/verification/99999').status_code==404
    assert c.post(path+'/challenge',json={'authorized':False}).status_code==400
    assert c.post(path+'/challenge',json={'authorized':'true'}).status_code==422
    assert c.post(path+'/check').status_code==409
    assert c.post(path+'/challenge',json={'authorized':True},headers={'X-GhostLead-Request':'0'}).status_code==403
    p=c.post(path+'/challenge',json={'authorized':True}).json()
    assert p['status']=='pending' and p['record_name']=='_ghostlead-verification.www.example.com'
    assert p['record_value'].startswith('ghostlead-verification=')
    calls=[]
    def missing(h,t): calls.append((h,t));return 'not_found'
    monkeypatch.setattr(main.dv,'lookup_txt',missing)
    assert c.post(path+'/check').json()['last_result']=='not_found'
    assert calls==[('www.example.com',p['record_value'])]
    assert c.post(path+'/check').status_code==429
    q=c.post(path+'/challenge',json={'authorized':True}).json()
    assert q['record_value']!=p['record_value']
    monkeypatch.setattr(main.dv,'lookup_txt',lambda h,t:'dns_error')
    assert c.post(path+'/check').json()['last_result']=='dns_error'
    c.post(path+'/challenge',json={'authorized':True})
    monkeypatch.setattr(main.dv,'lookup_txt',lambda h,t:'matched')
    v=c.post(path+'/check').json()
    assert v['status']=='verified' and v['verified_until']>int(time.time())
    assert c.get(path).json()['status']=='verified'
    assert c.post(path+'/check').status_code==409
    from sqlalchemy.orm import Session
    with Session(main.engine) as s:
        row=s.get(main.DomainProof,i);row.verified_until=int(time.time())-1;s.commit()
    assert c.get(path).json()['status']=='expired'
    assert c.delete(path).json()['status']=='unverified'
    assert c.get('/api/workspace').json()['runs']==[]
    c.post(path+'/challenge',json={'authorized':True})
    assert c.delete('/api/records/websites/'+str(i)).status_code==200
    assert c.get(path).status_code==404
    with Session(main.engine) as s:assert s.get(main.DomainProof,i) is None


def test_expired_and_replaced_challenge(workspace,monkeypatch):
    main,c,i=workspace;path=f'/api/verification/{i}'
    p=c.post(path+'/challenge',json={'authorized':True}).json()
    from sqlalchemy.orm import Session
    with Session(main.engine) as s:
        s.get(main.DomainProof,i).issued_at=int(time.time())-main.dv.CHALLENGE_SECONDS-1;s.commit()
    assert c.get(path).json()['status']=='expired'
    assert c.post(path+'/check').status_code==409
    p=c.post(path+'/challenge',json={'authorized':True}).json()
    def replaced(h,t):
        with Session(main.engine) as s:
            s.get(main.DomainProof,i).token='replacement';s.commit()
        return 'matched'
    monkeypatch.setattr(main.dv,'lookup_txt',replaced)
    assert c.post(path+'/check').status_code==409
    assert c.get(path).json()['status']=='pending'


def test_hostname_and_dns_parser(workspace,monkeypatch):
    main,_,_=workspace;dv=main.dv
    assert dv.hostname_for('https://WWW.Example.com./path')=='www.example.com'
    assert dv.hostname_for('https://bücher.example.com')=='xn--bcher-kva.example.com'
    for url in ['http://localhost','http://127.0.0.1','http://[::1]','http://169.254.169.254','http://service.local','http://example.invalid','https://example.com:8080','http://user@example.com','http://bad_label.example.com','http://123.123']:
        with pytest.raises(ValueError):dv.hostname_for(url)
    observed=[]
    def resolve(name,rdtype,**kwargs):
        observed.append((name,rdtype,kwargs));return [SimpleNamespace(strings=[b'ghostlead-',b'challenge']),SimpleNamespace(strings=[b'unrelated'])]
    monkeypatch.setattr(dv,'public_resolve',resolve)
    assert dv.lookup_txt('www.example.com','ghostlead-challenge')=='matched'
    assert dv.lookup_txt('www.example.com','ghostlead')=='not_found'
    assert observed[0]==('_ghostlead-verification.www.example.com.','TXT',{'lifetime':5.0})
    def timeout(*a,**k):raise dv.dns.exception.Timeout()
    monkeypatch.setattr(dv,'public_resolve',timeout)
    assert dv.lookup_txt('www.example.com','anything')=='dns_timeout'


def test_upgrade_existing_schema(workspace,tmp_path,monkeypatch):
    import os, subprocess, sys, sqlite3
    from pathlib import Path
    main,_,_=workspace
    path=tmp_path/'previous.db'
    old=create_engine('sqlite:///'+str(path))
    main.Base.metadata.create_all(old,tables=[t for t in main.Base.metadata.sorted_tables if t.name not in {'domain_proofs','dns_snapshots'}])
    with old.begin() as c:
        c.execute(main.Site.__table__.insert(),dict(id=42,name='Existing website',url='https://www.example.com',created_at='2026-11-24T00:00:00Z'))
    old.dispose()
    env={**os.environ,'GHOSTLEAD_DATABASE_URL':'sqlite:///'+str(path)}
    subprocess.run([sys.executable,'-c','from app.main import engine; engine.dispose()'],cwd=Path(main.__file__).resolve().parents[1],env=env,check=True,timeout=20)
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT id,name,url FROM sites').fetchall()==[(42,'Existing website','https://www.example.com')]
        assert c.execute('SELECT COUNT(*) FROM domain_proofs').fetchone()==(0,)
