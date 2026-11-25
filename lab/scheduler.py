"""Finite foreground scheduling for the fixed GhostLead Lab, never external URLs."""
import argparse
from contextlib import contextmanager
import json
import signal
import socket
import sys
import time
import uuid
from . import monitoring

MIN_INTERVAL, MAX_INTERVAL, MAX_RUNS = 5, 3600, 100
LOCK_PORT = 5502


class StopFlag:
    """Signal handler sets only a boolean; wait uses a monotonic deadline."""
    requested = False

    def is_set(self):
        return self.requested

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.requested:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.1, remaining))
        return self.requested


class SchedulerBusy(RuntimeError):
    pass


@contextmanager
def scheduler_guard():
    """Hold a local TCP bind as a process-lifetime exclusion guard; no listener."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as guard:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            guard.bind(('127.0.0.1', LOCK_PORT))
        except OSError as exc:
            raise SchedulerBusy('scheduler_guard_unavailable') from exc
        yield


def validate(interval, runs):
    if type(interval) is not int or not MIN_INTERVAL <= interval <= MAX_INTERVAL:
        raise ValueError('interval must be an integer from 5 to 3600 seconds')
    if type(runs) is not int or not 1 <= runs <= MAX_RUNS:
        raise ValueError('runs must be an integer from 1 to 100')


def schedule(interval, runs, stop, emit, *, runner=None):
    """Run immediately, then wait interruptibly after each finished run.

    The CLI holds the process guard. Injected runner is for isolated tests only.
    No persistence, parallel workers, automatic retries or catch-up scheduling.
    """
    validate(interval, runs)
    runner = monitoring.run_monitoring if runner is None else runner
    session = str(uuid.uuid4())
    counts = dict(completed=0, partial=0, failed=0)

    def event(kind, **fields):
        emit(dict(schema_version=1, scope='local_lab_only', session_id=session,
                  event=kind, timestamp=monitoring.utc_now(), **fields))

    event('session_started', interval_seconds=interval, requested_runs=runs,
          schedule_mode='fixed_delay')
    reason = 'run_limit_reached'
    for index in range(1, runs + 1):
        if stop.is_set():
            reason = 'stop_requested'
            break
        event('run_started', sequence=index)
        try:
            result = runner()
            status = result['execution_status']
            if status not in counts or result.get('scope') != 'local_lab_only':
                raise ValueError('invalid monitor result')
        except Exception:
            # Unexpected execution exceptions do not leak internals or end scheduling.
            result = None
            status = 'failed'
        counts[status] += 1
        event('run_finished', sequence=index, execution_status=status,
              result=result, scheduler_error='monitor_execution_error' if result is None else None)
        if stop.is_set():
            reason = 'stop_requested'
            break
        if index < runs:
            event('waiting', delay_seconds=interval, next_sequence=index + 1)
            if stop.wait(interval):
                reason = 'stop_requested'
                break
    event('session_stopped', reason=reason, attempted_runs=sum(counts.values()), counts=counts)
    return 130 if reason == 'stop_requested' else 1 if counts['failed'] else 2 if counts['partial'] else 0


def main():
    parser = argparse.ArgumentParser(description='Schedule only GhostLead Lab monitoring. No external target supported.')
    parser.add_argument('--interval-seconds', type=int, default=30)
    parser.add_argument('--runs', type=int, default=3)
    args = parser.parse_args()
    try:
        validate(args.interval_seconds, args.runs)
    except ValueError as exc:
        parser.error(str(exc))
    stop = StopFlag()
    previous = {}

    def request_stop(signum, frame):
        stop.requested = True

    def emit(event):
        print(json.dumps(event, allow_nan=False, separators=(',', ':')), flush=True)

    try:
        with scheduler_guard():
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, request_stop)
            return schedule(args.interval_seconds, args.runs, stop, emit)
    except SchedulerBusy:
        print('Scheduler unavailable: port 5502 is reserved by another process.', file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 1
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
