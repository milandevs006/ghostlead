"""Release-gate integration: real loopback HTTP, offline evidence, disposable DB."""
import json
import sqlite3
import subprocess
import sys
import threading

from lab import evidence
from lab.server import LabServer


def test_scheduler_to_persistent_evidence_and_backup(tmp_path):
    log = tmp_path / 'observations.jsonl'
    db_path = tmp_path / 'evidence.sqlite3'
    with LabServer() as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'lab.scheduler', '--interval-seconds', '5', '--runs', '2'],
                capture_output=True, timeout=85,
            )
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            assert not server.events
            assert server.token.encode() not in result.stdout
        finally:
            server.shutdown()
            thread.join(timeout=3)
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert events[-1]['counts'] == dict(completed=2, partial=0, failed=0)
    log.write_bytes(result.stdout)
    runs, missing = evidence.read_runs(log)
    assert missing == 0 and len(runs) == 2
    db = evidence.connect(db_path)
    try:
        assert evidence.ingest(db, runs) == dict(inserted=2, duplicates=0, opened=3, repeated=3, recovered=0)
        assert evidence.ingest(db, runs)['duplicates'] == 2
    finally:
        db.close()
    # Reopen the exact database and back it up using SQLite, not a live file copy.
    db = evidence.connect(db_path)
    backup_path = tmp_path / 'backup.sqlite3'
    backup = sqlite3.connect(backup_path)
    try:
        db.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        backup.close()
        db.close()
    restored = evidence.connect(backup_path)
    try:
        report = evidence.summary(restored)
        assert report['runs'] == {'completed': 2}
        assert report['open_incidents'] == 3 and report['recovered_incidents'] == 0
        assert all(i['occurrences'] == 2 for i in report['recent_incidents'])
        assert len(report['recent_timeline']) == 6
    finally:
        restored.close()
