import json
import subprocess
import sys
import threading
import uuid
from unittest.mock import Mock

import pytest
from lab import scheduler as s
from lab.server import LabServer


class FakeStop:
    def __init__(self, stopped=False, stop_on_wait=False):
        self.stopped = stopped
        self.stop_on_wait = stop_on_wait
        self.waits = []

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.waits.append(seconds)
        self.stopped = self.stop_on_wait
        return self.stopped


def result(status='completed'):
    return {'scope':'local_lab_only','execution_status':status,
            'run_id':str(uuid.uuid4()),'observed_health':'issues_detected'}


@pytest.mark.parametrize('interval,runs',[(4,1),(3601,1),(5,0),(5,101),(True,1),(5,True),(5.0,1)])
def test_invalid_bounds(interval,runs):
    with pytest.raises(ValueError):
        s.validate(interval,runs)


def test_boundary_values():
    s.validate(5,1); s.validate(3600,100)


def test_order_and_fixed_delay():
    events=[]; stop=FakeStop()
    def run():
        assert events[-1]['event']=='run_started'
        return result()
    assert s.schedule(5,3,stop,events.append,runner=run)==0
    assert [e['event'] for e in events]==['session_started','run_started','run_finished','waiting',
        'run_started','run_finished','waiting','run_started','run_finished','session_stopped']
    assert stop.waits==[5,5]
    assert len({e['session_id'] for e in events})==1
    assert len({e['result']['run_id'] for e in events if e['event']=='run_finished'})==3
    assert events[-1]['counts']==dict(completed=3,partial=0,failed=0)


@pytest.mark.parametrize('states,code', [(['completed','completed'],0),(['partial','completed'],2),(['partial','failed'],1)])
def test_outcome_codes(states,code):
    events=[]
    assert s.schedule(5,2,FakeStop(),events.append,runner=Mock(side_effect=[result(x) for x in states]))==code
    assert events[-1]['attempted_runs']==2


def test_pre_stopped():
    events=[]; runner=Mock()
    assert s.schedule(5,2,FakeStop(stopped=True),events.append,runner=runner)==130
    runner.assert_not_called(); assert events[-1]['attempted_runs']==0


def test_stop_during_wait():
    events=[]; runner=Mock(return_value=result())
    assert s.schedule(5,3,FakeStop(stop_on_wait=True),events.append,runner=runner)==130
    assert runner.call_count==1 and events[-1]['reason']=='stop_requested'


def test_stop_during_run_finishes_current():
    events=[]; stop=FakeStop()
    def run():
        stop.stopped=True
        return result()
    assert s.schedule(5,3,stop,events.append,runner=run)==130
    assert stop.waits==[] and events[-1]['attempted_runs']==1
    assert events[-2]['event']=='run_finished'


def test_unexpected_failure_is_redacted_and_next_run_continues():
    events=[]
    assert s.schedule(5,2,FakeStop(),events.append,runner=Mock(side_effect=[RuntimeError('private secret'),result()]))==1
    assert events[2]['scheduler_error']=='monitor_execution_error'
    assert events[2]['result'] is None and 'private secret' not in json.dumps(events)
    assert events[-1]['counts']==dict(completed=1,partial=0,failed=1)


def test_wrong_scope_rejected():
    events=[]
    assert s.schedule(5,1,FakeStop(),events.append,runner=lambda:dict(result(),scope='external'))==1
    assert events[2]['result'] is None


def test_guard_cross_process_and_release():
    with s.scheduler_guard():
        with pytest.raises(s.SchedulerBusy):
            with s.scheduler_guard(): pass
        cp=subprocess.run([sys.executable,'-m','lab.scheduler','--runs','1'],capture_output=True,timeout=5)
        assert cp.returncode==1 and not cp.stdout and b'5502' in cp.stderr
    with s.scheduler_guard(): pass


@pytest.mark.parametrize('args',[['https://example.com'],['--interval-seconds','0'],['--runs','101']])
def test_cli_rejects_invalid_args(args):
    cp=subprocess.run([sys.executable,'-m','lab.scheduler',*args],capture_output=True,timeout=5)
    assert cp.returncode==2 and not cp.stdout


def test_live_two_runs():
    with LabServer() as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            cp=subprocess.run([sys.executable,'-m','lab.scheduler','--interval-seconds','5','--runs','2'],capture_output=True,timeout=85)
            assert cp.returncode==0,cp.stderr.decode()
            events=[json.loads(line) for line in cp.stdout.splitlines()]
            runs=[e['result'] for e in events if e['event']=='run_finished']
            assert len(runs)==2 and runs[0]['run_id']!=runs[1]['run_id']
            from datetime import datetime
            gap=(datetime.fromisoformat(runs[1]['started_at'])-datetime.fromisoformat(runs[0]['finished_at'])).total_seconds()
            assert gap>=4.9
            assert all(r['observed_health']=='issues_detected' and r['analysis']['summary']['findings']==3 for r in runs)
            assert events[-1]['counts']==dict(completed=2,partial=0,failed=0)
            assert not server.events and server.token not in cp.stdout.decode()
        finally:
            server.shutdown();thread.join(timeout=3)
