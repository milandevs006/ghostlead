import json
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from unittest.mock import Mock
import pytest
from lab import monitoring as m
from lab.server import LabServer


def sample(status=200,elapsed=12,error=None,truncated=False):
    return {'schema_version':1,'scope':'local_lab_only','origin':m.discovery.origin(),
            'observed_at':'2026-01-01T00:00:00+00:00','truncated':truncated,
            'pages':[{'path':'/','status':status,'elapsed_ms':elapsed,'error':error,'links':[]}]}


@pytest.mark.parametrize('status,elapsed,error,truncated,execution,health',[
    (200,12,None,False,'completed','no_issues_observed'),
    (200,1000,None,False,'completed','issues_detected'),
    (503,12,None,False,'completed','issues_detected'),
    (404,12,None,False,'completed','issues_detected'),
    (302,12,'redirect_not_followed',False,'partial','unknown'),
    (None,None,'TimeoutError',False,'partial','unknown'),
    (200,12,None,True,'partial','unknown'),
    (503,12,None,True,'partial','issues_detected'),
    (200,12,'response_too_large',False,'partial','unknown'),
])
def test_execution_vs_health(monkeypatch,status,elapsed,error,truncated,execution,health):
    monkeypatch.setattr(m,'discover_in_worker',lambda:sample(status,elapsed,error,truncated))
    r=m.run_monitoring()
    assert (r['execution_status'],r['observed_health'])==(execution,health)
    assert r['error_code'] is None and r['analysis'] is not None
    assert r['coverage']==('limited' if execution=='partial' else 'observed_links_only')
    assert uuid.UUID(r['run_id']).version==4
    assert datetime.fromisoformat(r['started_at']) <= datetime.fromisoformat(r['finished_at'])
    assert r['duration_ms']>=0


def test_unique_runs(monkeypatch):
    monkeypatch.setattr(m,'discover_in_worker',sample)
    assert m.run_monitoring()['run_id']!=m.run_monitoring()['run_id']


@pytest.mark.parametrize('exc,code',[(subprocess.TimeoutExpired('worker',32),'worker_timeout'),
    (OSError('private info'),'worker_start_failed'),(m.WorkerError('discovery_failed'),'discovery_failed')])
def test_failure_envelope(monkeypatch,exc,code):
    monkeypatch.setattr(m,'discover_in_worker',Mock(side_effect=exc))
    r=m.run_monitoring()
    assert r['execution_status']=='failed' and r['observed_health']=='unknown'
    assert r['analysis'] is None and r['error_code']==code and 'private info' not in json.dumps(r)


@pytest.mark.parametrize('patch',[{'origin':'https://example.com'},{'scope':'external'},{'pages':[]},{'truncated':'false'}])
def test_invalid_scope_or_schema(monkeypatch,patch):
    monkeypatch.setattr(m,'discover_in_worker',lambda:dict(sample(),**patch))
    assert m.run_monitoring()['error_code']=='invalid_worker_output'


def test_external_link_rejected(monkeypatch):
    data=sample();data['pages'][0]['links']=['https://example.com/']
    monkeypatch.setattr(m,'discover_in_worker',lambda:data)
    assert m.run_monitoring()['error_code']=='invalid_worker_output'


def test_worker_command(monkeypatch):
    mock=Mock(return_value=subprocess.CompletedProcess([],0,json.dumps(sample()).encode(),b''))
    monkeypatch.setattr(m.subprocess,'run',mock)
    assert m.discover_in_worker()['scope']=='local_lab_only'
    mock.assert_called_once_with([sys.executable,'-m','lab.discovery'],capture_output=True,timeout=32,check=False)


def test_worker_bad_json(monkeypatch):
    monkeypatch.setattr(m.subprocess,'run',Mock(return_value=subprocess.CompletedProcess([],0,b'not json',b'')))
    assert m.run_monitoring()['error_code']=='invalid_worker_output'


def test_live_worker():
    with LabServer() as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            cp=subprocess.run([sys.executable,'-m','lab.monitoring'],capture_output=True,timeout=40)
            r=json.loads(cp.stdout)
            assert cp.returncode==0 and r['execution_status']=='completed'
            assert r['observed_health']=='issues_detected' and r['analysis']['summary']['pages']==7
            assert r['analysis']['summary']['broken_link']==r['analysis']['summary']['server_error']==r['analysis']['summary']['slow']==1
            assert not server.events and server.token not in cp.stdout.decode()
        finally:
            server.shutdown();thread.join(timeout=3)


def test_cli_rejects_target():
    cp=subprocess.run([sys.executable,'-m','lab.monitoring','https://example.com'],capture_output=True,timeout=5)
    assert cp.returncode==2 and not cp.stdout
