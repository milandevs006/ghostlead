"""Loopback-only integration tests. No GhostLead database or external network."""
from threading import Thread
from urllib.request import urlopen, Request, ProxyHandler, build_opener
from urllib.error import HTTPError
from urllib.parse import urlencode
import json
import time
import pytest
from lab.server import LabServer

@pytest.fixture
def fixture_site():
    with LabServer(0) as server:
        thread=Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try: yield server, f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            thread.join(timeout=3)

opener = build_opener(ProxyHandler({}))
def request(base, path, data=None, headers=None):
    req=Request(base+path, data=urlencode(data).encode() if data is not None else None, headers=headers or {})
    try:
        with opener.open(req, timeout=5) as res: return res.status, res.read()
    except HTTPError as res:
        with res: return res.code, res.read()

@pytest.mark.parametrize('path,status',[('/',200),('/pricing',200),('/contact',200),('/broken',404),('/unavailable',503),('/api/health',200)])
def test_pages(fixture_site,path,status):
    _,base=fixture_site
    assert request(base,path)[0]==status

def test_slow(fixture_site):
    _,base=fixture_site
    start=time.monotonic()
    assert request(base,'/slow')[0]==200
    assert time.monotonic()-start>=1.9

@pytest.mark.parametrize('scenario,status,source,destination',[('delivered',200,True,True),('dropped',200,True,False),('rejected',422,False,False)])
def test_delivery(fixture_site,scenario,status,source,destination):
    server,base=fixture_site
    assert request(base,'/api/enquiry',{'token':server.token,'lead_id':'test-001','scenario':scenario})[0]==status
    assert json.loads(request(base,'/api/results')[1])['events']==[{'lead_id':'test-001','scenario':scenario,'source':source,'destination':destination}]

@pytest.mark.parametrize('override,headers,status',[({'token':'invalid'},{},403),({'lead_id':'real-user@example.com'},{},400),({'scenario':'unknown'},{},400),({}, {'Origin':'https://example.invalid'},403),({}, {'Host':'example.invalid'},403)])
def test_invalid(fixture_site,override,headers,status):
    server,base=fixture_site
    payload={'token':server.token,'lead_id':'test-001','scenario':'delivered'}|override
    assert request(base,'/api/enquiry',payload,headers)[0]==status
    assert not server.events

def test_retention(fixture_site):
    server,base=fixture_site
    for i in range(101):
        assert request(base,'/api/enquiry',{'token':server.token,'lead_id':f'test-{i}','scenario':'delivered'})[0]==200
    assert len(server.events)==100
    assert server.events[0]['lead_id']=='test-1'
