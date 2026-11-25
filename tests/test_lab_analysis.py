import threading
import pytest
from lab import analysis as a, discovery as d
from lab.server import LabServer


def page(path='/', status=200, ms=10, error=None, links=()):
    return dict(path=path,status=status,elapsed_ms=ms,error=error,links=list(links))


def report(*pages, truncated=False):
    return dict(scope='local_lab_only',origin=d.origin(),schema_version=1,pages=list(pages),observed_at='2026-01-01T00:00:00+00:00',truncated=truncated)


@pytest.mark.parametrize('status,ms,error,category',[(200,999,None,'healthy'),(200,1000,None,'slow'),(404,10,None,'missing_page'),(503,10,None,'server_error'),(403,10,None,'client_error'),(302,10,'redirect_not_followed','redirect_unchecked'),(None,None,'TimeoutError','incomplete'),(200,10,'response_too_large','incomplete'),(200,None,None,'incomplete'),(410,10,None,'missing_page')])
def test_classification(status,ms,error,category):
    assert a.analyse(report(page(status=status,ms=ms,error=error)))['pages'][0]['category']==category


def test_referrers():
    r=a.analyse(report(page(links=['/x','/x']),page('/b',links=['/x']),page('/x',404)))
    assert r['summary']['broken_link']==1
    assert r['findings'][0]['referrers']==['/','/b']


def test_percentiles():
    r=a.analyse(report(page(ms=100),page('/b',ms=200),page('/c',ms=300),page('/d',503,9000)))
    assert r['latency_ms']==dict(sample_count=3,min=100,median=200,p95=290.0,max=300)


def test_empty_and_truncated():
    r=a.analyse(report(truncated=True))
    assert r['truncated'] and r['latency_ms']['p95'] is None and r['summary']['pages']==0


def test_scope_rejected():
    r=report();r['origin']='https://example.com'
    with pytest.raises(ValueError):a.analyse(r)


def test_html_escape():
    r=a.analyse(report(page('/<script>',status=503)))
    h=a.render_html(r)
    assert '<script>' not in h and '&lt;script&gt;' in h


def test_live_lab(monkeypatch):
    with LabServer(0) as server:
        monkeypatch.setattr(d,'PORT',server.server_port)
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            r=a.analyse(d.discover())
            assert r['summary']['pages']==7 and r['summary']['broken_link']==1 and r['summary']['server_error']==1
            assert next(p for p in r['pages'] if p['path']=='/slow')['category']=='slow'
            assert r['latency_ms']['sample_count']==5 and not server.events
            assert server.token not in a.render_html(r)
        finally:server.shutdown();t.join(timeout=3)
