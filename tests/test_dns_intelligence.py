"""All DNS responses are mocked. No external requests or workspace data."""
import dns.resolver
import dns.exception
from types import SimpleNamespace
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from test_domain_verification import workspace


def test_public_lookup_and_history(workspace, monkeypatch):
    main,c,i=workspace
    monkeypatch.setattr(main,'_dns_next',0.0)
    di=main.di
    calls=[]
    def resolve(name, kind, lifetime):
        calls.append((name,kind,lifetime))
        if kind=='AAAA': raise dns.resolver.NoAnswer()
        if kind=='MX': raise dns.exception.Timeout()
        if kind=='DS': raise dns.resolver.NXDOMAIN()
        if kind=='CNAME': raise dns.resolver.NoNameservers()
        value='ns15.domaincontrol.com.' if kind=='NS' else 'fixture'
        class Answer(list): rrset=SimpleNamespace(ttl=600)
        return Answer([SimpleNamespace(to_text=lambda:value)])
    monkeypatch.setattr(di,'public_resolve',resolve)
    p=f'/api/intelligence/{i}'
    assert TestClient(main.app).get(p).status_code==401
    assert TestClient(main.app,headers={'X-GhostLead-Request':'1'}).post(p+'/lookup').status_code==401
    assert c.get(p).json()['history']==[]
    assert c.get(p).json()['verification_status']=='unverified'
    assert c.post(p+'/lookup',headers={'X-GhostLead-Request':'0'}).status_code==403
    r=c.post(p+'/lookup');assert r.status_code==200,r.text
    snap=r.json();assert snap['provider_hint']=='GoDaddy' and snap['resolver']=='8.8.8.8'
    status={x['type']:x['status'] for x in snap['records']}
    assert status['AAAA']=='no_answer' and status['MX']=='timeout' and status['DS']=='nxdomain' and status['CNAME']=='resolver_error'
    assert len(calls)==9 and all(call[0].endswith('.') for call in calls)
    assert c.get(p).json()['history']==[snap]
    assert c.post(p+'/lookup').status_code==429
    assert c.get('/api/workspace').json()['runs']==[]
    assert c.get(f'/api/verification/{i}').json()['status']=='unverified'
    with Session(main.engine) as s:
        for _ in range(24): s.add(main.DnsSnapshot(site_id=i,observed_at=main.now(),payload='{}'))
        s.commit()
    monkeypatch.setattr(main,'_dns_next',0.0)
    assert c.post(p+'/lookup').status_code==200
    assert len(c.get(p).json()['history'])==20
    assert c.delete('/api/records/websites/'+str(i)).status_code==200
    with Session(main.engine) as s: assert s.query(main.DnsSnapshot).count()==0


def test_verification_dns_diagnostics(workspace,monkeypatch):
    main,_,_=workspace
    for exc,result in [(dns.resolver.NXDOMAIN,'missing_name'),(dns.resolver.NoAnswer,'missing_record'),(dns.exception.Timeout,'dns_timeout'),(dns.resolver.NoNameservers,'dns_error')]:
        def fail(*a,**kw): raise exc()
        monkeypatch.setattr(main.dv,'public_resolve',fail)
        assert main.dv.lookup_txt('example.com','test')==result
    # A fixed resolver must be used; no system configuration or custom target resolver.
    import importlib
    original=importlib.reload(main.dv)
    captured={}
    class Resolver:
        def __init__(self,configure): captured['configure']=configure
        def resolve(self,name,kind,**kw): captured.update(nameservers=self.nameservers,name=name,kind=kind,**kw);return []
    monkeypatch.setattr(original.dns.resolver,'Resolver',Resolver)
    original.public_resolve('example.com.','A',3)
    assert captured=={'configure':False,'nameservers':['8.8.8.8'],'name':'example.com.','kind':'A','search':False,'lifetime':3}
