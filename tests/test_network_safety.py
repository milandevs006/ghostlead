import time
from types import SimpleNamespace
import pytest
import dns.resolver
import dns.exception
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_domain_verification import workspace
from app import network_safety as ns

@pytest.mark.parametrize('url', ['http://127.0.0.1','http://[::1]','http://169.254.169.254','http://localhost','http://host.local','https://user@www.example.com','https://www.example.com:8080','https://www.example.com\\@evil.example.com','https://www.example.com/#x','https://www.example.com/%0a','https://www.example.com./','https://www.example.com/%5c'])
def test_url_blocks(url):
    with pytest.raises(ns.SafetyError): ns.validate_url(url)

@pytest.mark.parametrize('address',['0.0.0.0','10.0.0.1','127.0.0.1','169.254.169.254','172.16.0.1','192.168.0.1','100.64.0.1','224.0.0.1','240.0.0.1','192.0.2.1','::1','fc00::1','fe80::1','::ffff:8.8.8.8','2002:0808:0808::1','64:ff9b::808:808','ff02::1','2001:db8::1','3fff::1'])
def test_ip_blocks(address):
    assert not ns.address_allowed(address)

def test_public_resolution_and_redirect(monkeypatch):
    t=ns.validate_url('https://www.example.com/form')
    assert ns.address_allowed('8.8.8.8') and ns.address_allowed('2606:4700:4700::1111')
    monkeypatch.setattr(ns,'public_resolve',lambda name,kind,lifetime:[SimpleNamespace(address='8.8.8.8' if kind=='A' else '2606:4700:4700::1111')])
    assert len(ns.resolve_addresses(t))==2
    assert ns.validate_redirect(t,t,'/contact',0).url=='https://www.example.com/contact'
    for dest in ['//other.example.com','http://www.example.com','https://127.0.0.1','/bad%0a']:
        with pytest.raises(ns.SafetyError):ns.validate_redirect(t,t,dest,0)
    with pytest.raises(ns.SafetyError):ns.validate_redirect(t,t,'/contact',3)
    monkeypatch.setattr(ns,'public_resolve',lambda *a,**k:[SimpleNamespace(address='8.8.8.8'),SimpleNamespace(address='10.0.0.1')])
    with pytest.raises(ns.SafetyError): ns.resolve_addresses(t)
    def timeout(name,kind,lifetime):
        if kind=='AAAA':raise dns.exception.Timeout()
        return [SimpleNamespace(address='8.8.8.8')]
    monkeypatch.setattr(ns,'public_resolve',timeout)
    with pytest.raises(ns.SafetyError):ns.resolve_addresses(t)
    def missing(name,kind,lifetime):raise dns.resolver.NoAnswer()
    monkeypatch.setattr(ns,'public_resolve',missing)
    with pytest.raises(ns.SafetyError):ns.resolve_addresses(t)

def test_safety_api(workspace,monkeypatch):
    main,c,i=workspace; p=f'/api/safety/{i}'; v=f'/api/verification/{i}'
    calls=[]
    monkeypatch.setattr(ns,'resolve_addresses',lambda target: calls.append(target.hostname) or ('8.8.8.8',))
    assert TestClient(main.app).get(p).status_code==401
    assert c.get(p).json()['can_preflight'] is False
    monkeypatch.setattr(main,'_safety_next',0.)
    assert c.post(p+'/preflight').json()['history'][0]['outcome']=='blocked'
    assert not calls
    assert c.post(p+'/preflight').status_code==429
    c.post(v+'/challenge',json={'authorized':True})
    monkeypatch.setattr(main.dv,'lookup_txt',lambda *a:'matched')
    assert c.post(v+'/check').json()['status']=='verified'
    monkeypatch.setattr(main,'_safety_next',0.)
    r=c.post(p+'/preflight').json();assert r['history'][0]['outcome']=='passed' and r['http_enabled'] is False
    assert calls==['www.example.com']
    def revoked(t):
        with Session(main.engine) as s:
            s.delete(s.get(main.DomainProof,i));s.commit()
        return ('8.8.8.8',)
    monkeypatch.setattr(ns,'resolve_addresses',revoked)
    monkeypatch.setattr(main,'_safety_next',0.)
    assert c.post(p+'/preflight').json()['history'][0]['outcome']=='blocked'
    assert c.get('/api/workspace').json()['runs']==[]
    with Session(main.engine) as s:
        for _ in range(35):s.add(main.SafetyAudit(site_id=i,observed_at=main.now(),outcome='blocked',reason='fixture',address_count=0))
        s.commit()
    monkeypatch.setattr(main,'_safety_next',0.)
    assert len(c.post(p+'/preflight').json()['history'])==30
    assert c.delete(f'/api/records/websites/{i}').status_code==200
    with Session(main.engine) as s: assert s.query(main.SafetyAudit).count()==0
