import json
import threading
import pytest
from lab import discovery as d
from lab.server import LabServer

@pytest.fixture
def local_lab(monkeypatch):
    with LabServer(0) as server:
        monkeypatch.setattr(d, 'PORT', server.server_port)
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try: yield server
        finally: server.shutdown();t.join(timeout=3)

@pytest.mark.parametrize('target', ['https://example.com/', '//example.com/path', 'http://127.0.0.1:8000/', 'http://localhost:5501/', '/x?secret=1', '/%2e%2e/x', '/a\\b'])
def test_out_of_scope(target):
    assert d.local_path('/',target) is None

def test_local_paths():
    assert d.local_path('/pricing','/contact#form')=='/contact'
    assert d.local_path('/','/pricing')=='/pricing'

def test_parser_no_values():
    p=d.Structure('/contact');p.feed('<title>Contact</title><form action="/api/enquiry" method="post"><input name="token" type="hidden" value="secret"><input name="id" required><a href="https://example.com">external</a></form>')
    assert p.title=='Contact' and p.skipped==1
    assert p.forms[0]['action']=='/api/enquiry' and p.forms[0]['method']=='POST'
    assert p.forms[0]['fields'][1]['required']
    assert 'secret' not in json.dumps(p.forms)

def test_live_discovery(local_lab):
    report=d.discover();pages={p['path']:p for p in report['pages']}
    assert set(pages)=={'/','/pricing','/contact','/broken','/slow','/unavailable','/lab/results'}
    assert pages['/broken']['status']==404 and pages['/unavailable']['status']==503
    assert pages['/slow']['elapsed_ms']>=1800
    assert report['summary']['forms']==1 and report['summary']['http_errors']==2
    assert report['skipped_api_paths']==['/api/results']
    assert local_lab.token not in json.dumps(report)
    assert not local_lab.events and not report['truncated']

def test_wrong_service(monkeypatch):
    monkeypatch.setattr(d,'fetch',lambda *_: (200,'application/json',b'{"service":"other"}',0,None))
    with pytest.raises(RuntimeError): d.discover()

def test_limit(local_lab,monkeypatch):
    monkeypatch.setattr(d,'MAX_PAGES',1)
    r=d.discover();assert r['truncated'] and len(r['pages'])==1

def test_no_redirect_follow(monkeypatch):
    calls=[]
    class Response:
        status=302
    class Connection:
        def __init__(self,*a,**k): calls.append(a)
        def request(self,method,path,**kwargs): calls.append((method,path))
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(d.http.client,'HTTPConnection',Connection)
    import time
    assert d.fetch('/',time.monotonic()+2)[-1]=='redirect_not_followed'
    assert calls==[(d.HOST,d.PORT),('GET','/')]
