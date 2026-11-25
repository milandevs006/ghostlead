import copy
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from lab import analysis, discovery, evidence


def run(n=1, status=404, elapsed=3, execution='completed', error=None, absent=False):
    start=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=n*10)
    end=start+timedelta(seconds=2)
    pages=[dict(path='/',status=200,elapsed_ms=1,error=None,links=[] if absent else ['/target'])]
    if not absent:
        pages.append(dict(path='/target',status=status,elapsed_ms=elapsed,error=error,links=[]))
    report=analysis.analyse(dict(schema_version=1,scope='local_lab_only',origin=discovery.origin(),observed_at=start.isoformat(),truncated=False,pages=pages))
    return dict(schema_version=1,scope='local_lab_only',origin=discovery.origin(),run_id=str(uuid.UUID(int=n)),started_at=start.isoformat(),finished_at=end.isoformat(),duration_ms=2000,execution_status=execution,error_code='discovery_failed' if execution=='failed' else None,analysis=None if execution=='failed' else report)


@pytest.fixture
def db(tmp_path):
    conn=evidence.connect(tmp_path/'evidence.sqlite3')
    yield conn
    conn.close()


def add(db,*runs):
    return evidence.ingest(db,[evidence.normalize(r) for r in runs])


def test_open_repeat_recover_reopen(db):
    assert add(db,run())['opened']==1
    assert add(db,run(2))['repeated']==1
    assert evidence.summary(db)['recent_incidents'][0]['occurrences']==2
    assert add(db,run(3,200))['recovered']==1
    assert add(db,run(4))['opened']==1
    s=evidence.summary(db)
    assert (s['open_incidents'],s['recovered_incidents'])==(1,1)
    assert [x['event'] for x in s['recent_timeline']]==['opened','recovered','repeated','opened']


@pytest.mark.parametrize('later',[run(2,execution='failed'),run(2,200,execution='partial'),run(2,absent=True),run(2,None,execution='partial',error='TimeoutError'),run(2,302,execution='partial',error='redirect_not_followed')])
def test_no_false_recovery(db,later):
    add(db,run()); assert add(db,later)['recovered']==0
    assert evidence.summary(db)['open_incidents']==1


def test_category_change_does_not_recover(db):
    add(db,run(),run(2,503)); assert evidence.summary(db)['open_incidents']==2
    assert add(db,run(3,200))['recovered']==2


def test_duplicate_no_side_effect(db):
    r=run(); add(db,r); assert add(db,r)['duplicates']==1
    assert evidence.summary(db)['recent_incidents'][0]['occurrences']==1


def test_conflict_rolls_back_batch(db):
    add(db,run())
    with pytest.raises(ValueError,match='Conflicting'):
        add(db,run(2),run(1,503))
    assert evidence.summary(db)['runs']=={'completed':1}


def test_out_of_order_rejected(db):
    add(db,run(2))
    with pytest.raises(ValueError,match='chronological'):
        add(db,run())


def test_persistence(tmp_path):
    p=tmp_path/'test.sqlite3'; d=evidence.connect(p); add(d,run()); d.close()
    d=evidence.connect(p); assert evidence.summary(d)['open_incidents']==1; d.close()


def test_unrelated_database_not_modified(tmp_path):
    p=tmp_path/'other.sqlite3'; d=sqlite3.connect(p); d.execute('create table customers(id)'); d.close()
    with pytest.raises(ValueError,match='Not a GhostLead'):
        evidence.connect(p)
    d=sqlite3.connect(p); assert d.execute('select name from sqlite_master where type="table"').fetchall()==[('customers',)]; d.close()


@pytest.mark.parametrize('mutate',[
    lambda r:r.update(origin='https://example.com'),
    lambda r:r.update(scope='production'),
    lambda r:r.update(run_id='bad'),
    lambda r:r.update(finished_at='2025-01-01'),
    lambda r:r['analysis']['pages'][1].update(path='//external'),
    lambda r:r['analysis']['pages'][1].update(category='healthy'),
    lambda r:r['analysis']['pages'][1].update(elapsed_ms=float('nan')),
    lambda r:r['analysis']['pages'][1].update(referrers=['/missing']),
    lambda r:r['analysis'].update(truncated=True),
])
def test_reject_bad_evidence(mutate):
    r=run(); mutate(r)
    with pytest.raises(ValueError): evidence.normalize(r)


def event(r):
    return dict(schema_version=1,scope='local_lab_only',event='run_finished',execution_status=r['execution_status'],result=r)


def test_jsonl_bom_and_missing(tmp_path):
    p=tmp_path/'a.jsonl'; r=run()
    missing=dict(schema_version=1,scope='local_lab_only',event='run_finished',execution_status='failed',result=None,scheduler_error='monitor_execution_error')
    p.write_text('\n'.join(map(json.dumps,[event(r),missing])),encoding='utf-8-sig')
    runs,skipped=evidence.read_runs(p); assert len(runs)==skipped==1


def test_line_bound(tmp_path,monkeypatch):
    p=tmp_path/'a.jsonl'; p.write_text(' '*40)
    monkeypatch.setattr(evidence,'MAX_LINE',20)
    with pytest.raises(ValueError,match='bounds'): evidence.read_runs(p)


def test_run_limit(db,monkeypatch):
    monkeypatch.setattr(evidence,'MAX_STORED',1)
    with pytest.raises(ValueError,match='limit'): add(db,run(),run(2))
    assert evidence.summary(db)['runs']=={}


def test_real_saved_scheduler_schema(db,tmp_path):
    p=tmp_path/'events.jsonl'; p.write_text(json.dumps(event(run()))+'\n'+json.dumps(event(run(2)))+'\n')
    runs,skipped=evidence.read_runs(p); assert not skipped
    assert evidence.ingest(db,runs)==dict(inserted=2,duplicates=0,opened=1,repeated=1,recovered=0)
