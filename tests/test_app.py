"""Tests use a disposable database; no records are shipped with the app."""
import os, tempfile, atexit
from pathlib import Path
_tmp=tempfile.TemporaryDirectory()
atexit.register(_tmp.cleanup)
os.environ['GHOSTLEAD_DATABASE_URL']='sqlite:///'+str(Path(_tmp.name)/'test.db')
from fastapi.testclient import TestClient
from app.main import app

def test_workspace_lifecycle():
    c=TestClient(app,headers={'X-GhostLead-Request':'1'})
    assert c.get('/api/workspace').status_code==401
    assert c.get('/api/session').json()['configured'] is False
    assert c.post('/api/setup',json={'email':'test@example.invalid','password':'isolated-test-password','workspace':'Test only'}).status_code==200
    w=c.get('/api/workspace').json()
    assert all(w[k]==[] for k in ['websites','monitors','runs','lead_events','imports'])
    assert c.post('/api/setup',json={'email':'other@example.invalid','password':'isolated-test-password','workspace':'Other'}).status_code==409
    def add(k,**row):return c.post('/api/records/'+k,json=row)
    assert add('websites',name='Test site',url='https://example.invalid').status_code==200
    assert add('websites',name='Duplicate',url='https://example.invalid').status_code==409
    assert add('monitors',website_url='https://example.invalid',name='Form',kind='Contact form').status_code==200
    assert add('runs',website_url='https://example.invalid',monitor_name='Form',observed_at='2026-11-24T10:00:00Z',status='failed',latency_ms=200,detail='Test-only failure').status_code==200
    assert add('runs',website_url='https://example.invalid',monitor_name='Form',observed_at='2026-11-24T10:00:00',status='passed').status_code==400
    h='website_url,event_key,stage,observed_at\n'
    a='https://example.invalid,key,source,2026-11-24T10:00:00Z\n'
    b='https://example.invalid,key,destination,2026-11-24T10:01:00Z\n'
    bad='https://example.invalid,key2,invalid,2026-11-24T10:00:00Z\n'
    assert c.post('/api/import/lead_events',json={'filename':'bad.csv','content':h+a+bad}).status_code==400
    assert c.get('/api/workspace').json()['lead_events']==[]
    assert c.post('/api/import/lead_events',json={'filename':'good.csv','content':h+a+b}).json()=={'rows':2}
    w=c.get('/api/workspace').json(); assert len(w['lead_events'])==2 and len(w['imports'])==1
    site_id=w['websites'][0]['id']; route=f'/api/journeys/{site_id}'
    assert TestClient(app).get(route).status_code==401
    assert c.get(route).json()['nodes']==[]
    assert c.get(route).json()['revision']==0
    nodes=[{'id':'node-a','kind':'website','label':'Test input','x':0,'y':0}, {'id':'node-b','kind':'crm','label':'Test destination','x':240,'y':0}]
    edges=[{'id':'edge-a','source':'node-a','target':'node-b'}]
    graph={'revision':0,'nodes':nodes,'edges':edges}
    assert c.put(route,json={**graph,'edges':[{'id':'bad','source':'node-a','target':'missing'}]}).status_code==400
    assert c.get(route).json()['revision']==0
    saved=c.put(route,json=graph); assert saved.status_code==200 and saved.json()['revision']==1
    assert c.get(route).json()['nodes']==nodes
    assert c.put(route,json=graph).status_code==409
    assert c.put(route,json={**graph,'revision':1,'nodes':[],'edges':[]}).status_code==200
    assert c.get(route).json()['nodes']==[]
    assert c.put(route,json={**graph,'revision':2}).status_code==200
    assert c.delete('/api/records/websites/'+str(site_id)).status_code==200
    assert c.get(route).status_code==404
    from app.main import engine, JourneyLayout
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        assert db.get(JourneyLayout,site_id) is None
    w=c.get('/api/workspace').json();assert all(w[k]==[] for k in ['websites','monitors','runs','lead_events'])
    assert c.post('/api/logout').status_code==200
    assert c.get('/api/workspace').status_code==401
    assert c.post('/api/login',json={'email':'test@example.invalid','password':'wrong'}).status_code==401
    assert c.post('/api/login',json={'email':'test@example.invalid','password':'isolated-test-password'}).status_code==200
    assert TestClient(app).post('/api/logout').status_code==403
