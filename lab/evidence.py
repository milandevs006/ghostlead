"""Offline, bounded evidence ingestion for GhostLead Lab, never production data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import uuid
from . import analysis, discovery

MAX_FILE = 16 * 1024 * 1024
MAX_LINE = 256 * 1024
MAX_RUNS = 100
MAX_STORED = 10000
DB_PATH = Path.home() / '.ghostlead-lab' / 'evidence-v1.sqlite3'
ISSUES = {'broken_link', 'missing_page', 'server_error', 'client_error', 'slow'}
ERRORS = {'worker_timeout', 'discovery_failed', 'invalid_worker_output', 'worker_start_failed', 'analysis_failed'}


def require(ok, message='Invalid lab evidence'):
    if not ok:
        raise ValueError(message)


def stamp(value):
    require(isinstance(value, str) and len(value) <= 40)
    dt = datetime.fromisoformat(value)
    require(dt.tzinfo is not None and dt.utcoffset() is not None)
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds')


def valid_path(value):
    return (isinstance(value, str) and discovery.local_path('/', value) == value
            and value != '/api' and not value.startswith('/api/'))


def normalize(run):
    """Validate run schema, retain bounded observations, recompute classification."""
    require(isinstance(run, dict) and run.get('schema_version') == 1
            and run.get('scope') == 'local_lab_only' and run.get('origin') == discovery.origin())
    ident = run.get('run_id')
    require(isinstance(ident, str) and len(ident) == 36 and str(uuid.UUID(ident)) == ident)
    start, finish = stamp(run.get('started_at')), stamp(run.get('finished_at'))
    require(start <= finish)
    duration = run.get('duration_ms')
    require(type(duration) is int and 0 <= duration <= 600000)
    status, code, report = (run.get(k) for k in ('execution_status','error_code','analysis'))
    require(status in ('completed','partial','failed'))
    result = dict(run_id=ident, started_at=start, finished_at=finish, duration_ms=duration,
                  execution_status=status, error_code=code, pages=[])
    if status == 'failed':
        require(report is None and code in ERRORS)
        return result
    require(code is None and isinstance(report, dict) and report.get('schema_version') == 1
            and report.get('scope') == 'local_lab_only' and report.get('origin') == discovery.origin()
            and type(report.get('truncated')) is bool and report.get('slow_threshold_ms') == analysis.SLOW_MS)
    observed = stamp(report.get('observed_at'))
    require(start <= observed <= finish)
    pages = report.get('pages')
    require(isinstance(pages,list) and 1 <= len(pages) <= discovery.MAX_PAGES)
    source = {}
    for p in pages:
        require(isinstance(p,dict))
        path, http, elapsed, error, refs = (p.get(k) for k in ('path','status','elapsed_ms','error','referrers'))
        require(valid_path(path) and path not in source)
        require(http is None or (type(http) is int and 100 <= http <= 599))
        require(elapsed is None or (type(elapsed) in (int,float) and math.isfinite(elapsed) and 0 <= elapsed <= 600000))
        require(error is None or (isinstance(error,str) and 0 < len(error) <= 80 and error.isascii() and error.replace('_','').isalnum()))
        require(isinstance(refs,list) and len(refs) <= discovery.MAX_PAGES and all(valid_path(r) for r in refs))
        source[path] = dict(path=path,status=http,elapsed_ms=elapsed,error=error,links=[],referrers=refs)
    require('/' in source)
    for p in source.values():
        for ref in p['referrers']:
            require(ref in source)
            source[ref]['links'].append(p['path'])
    calculated = analysis.analyse(dict(schema_version=1,scope='local_lab_only',origin=discovery.origin(),
                                      observed_at=observed,truncated=report['truncated'],pages=list(source.values())))
    require(status != 'completed' or (not calculated['truncated'] and not any(p['error'] or p['category'] in ('incomplete','redirect_unchecked') for p in calculated['pages'])))
    for p, c in zip(pages, calculated['pages']):
        require(p.get('category') == c['category'] and p.get('severity') == c['severity'])
    result['pages'] = sorted(calculated['pages'],key=lambda p:p['path'])
    return result


def read_runs(path):
    """Accept saved scheduler JSONL; ignore non-result events, report missing results."""
    runs, skipped, total = [], 0, 0
    with open(path,'rb') as f:
        while raw := f.readline(MAX_LINE + 1):
            total += len(raw)
            require(len(raw) <= MAX_LINE and total <= MAX_FILE,'Evidence file exceeds bounds')
            if not raw.strip():
                continue
            event = json.loads(raw.decode('utf-8-sig'))
            require(isinstance(event,dict) and event.get('schema_version') == 1 and event.get('scope') == 'local_lab_only')
            kind = event.get('event')
            require(kind in ('session_started','run_started','run_finished','waiting','session_stopped'))
            if kind != 'run_finished':
                continue
            if event.get('result') is None:
                require(event.get('execution_status') == 'failed' and event.get('scheduler_error') == 'monitor_execution_error')
                skipped += 1
            else:
                run = normalize(event['result'])
                require(run['execution_status'] == event.get('execution_status'))
                runs.append(run)
            require(len(runs)+skipped <= MAX_RUNS,'Maximum 100 attempts per import')
    require(runs or skipped,'No monitoring results found')
    return runs, skipped


SCHEMA = '''
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, finished TEXT NOT NULL, status TEXT NOT NULL, digest TEXT NOT NULL, evidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, path TEXT NOT NULL, category TEXT NOT NULL, severity TEXT NOT NULL, opened TEXT NOT NULL, last_seen TEXT NOT NULL, recovered TEXT, occurrences INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_open ON incidents(path,category) WHERE recovered IS NULL;
CREATE TABLE IF NOT EXISTS timeline (id INTEGER PRIMARY KEY, incident_id INTEGER NOT NULL REFERENCES incidents(id), run_id TEXT NOT NULL REFERENCES runs(id), event TEXT NOT NULL, timestamp TEXT NOT NULL);
'''


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path,timeout=5)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        # Avoid writing to unrelated existing databases.
        marker = db.execute('PRAGMA application_id').fetchone()[0]
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        require(marker == 1196180812 or (marker == 0 and not tables),'Not a GhostLead Lab evidence database')
        db.executescript('BEGIN IMMEDIATE; PRAGMA application_id=1196180812; '+SCHEMA+'COMMIT;')
        return db
    except BaseException:
        db.close()
        raise


def ingest(db, runs):
    counts = dict(inserted=0,duplicates=0,opened=0,repeated=0,recovered=0)
    with db:
        db.execute('BEGIN IMMEDIATE')
        for run in runs:
            payload = json.dumps(run,sort_keys=True,separators=(',',':'),allow_nan=False)
            digest = hashlib.sha256(payload.encode()).hexdigest()
            ident, when = run['run_id'],run['finished_at']
            old = db.execute('SELECT digest FROM runs WHERE id=?',(ident,)).fetchone()
            if old:
                require(old['digest']==digest,'Conflicting evidence for existing run ID')
                counts['duplicates']+=1
                continue
            latest, n = db.execute('SELECT MAX(finished),COUNT(*) FROM runs').fetchone()
            require(latest is None or when > latest,'New runs must arrive in chronological order')
            require(n < MAX_STORED,'Evidence limit reached; archive the lab database before continuing')
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?)',(ident,when,run['execution_status'],digest,payload))
            counts['inserted']+=1
            for p in run['pages']:
                path, category = p['path'],p['category']
                if category in ISSUES:
                    row = db.execute('SELECT id FROM incidents WHERE path=? AND category=? AND recovered IS NULL',(path,category)).fetchone()
                    if row:
                        iid=row['id']; event='repeated'
                        db.execute('UPDATE incidents SET last_seen=?,occurrences=occurrences+1 WHERE id=?',(when,iid))
                    else:
                        iid=db.execute('INSERT INTO incidents(path,category,severity,opened,last_seen,occurrences) VALUES (?,?,?,?,?,1)',(path,category,p['severity'],when,when)).lastrowid
                        event='opened'
                    db.execute('INSERT INTO timeline(incident_id,run_id,event,timestamp) VALUES (?,?,?,?)',(iid,ident,event,when))
                    counts[event]+=1
                elif category=='healthy' and run['execution_status']=='completed':
                    for row in db.execute('SELECT id FROM incidents WHERE path=? AND recovered IS NULL',(path,)).fetchall():
                        iid=row['id']
                        db.execute('UPDATE incidents SET recovered=? WHERE id=?',(when,iid))
                        db.execute('INSERT INTO timeline(incident_id,run_id,event,timestamp) VALUES (?,?,?,?)',(iid,ident,'recovered',when))
                        counts['recovered']+=1
    return counts


def summary(db):
    counts = dict(db.execute('SELECT status,COUNT(*) FROM runs GROUP BY status').fetchall())
    total, opened = db.execute('SELECT COUNT(*),COUNT(*)-COUNT(recovered) FROM incidents').fetchone()
    return dict(scope='local_lab_only',runs=counts,open_incidents=opened,recovered_incidents=total-opened,
                recent_incidents=[dict(r) for r in db.execute('SELECT * FROM incidents ORDER BY id DESC LIMIT 100')],
                recent_timeline=[dict(r) for r in db.execute('SELECT * FROM timeline ORDER BY id DESC LIMIT 100')])


def main():
    parser=argparse.ArgumentParser(description='Offline GhostLead Lab evidence; no external targets or production database.')
    sub=parser.add_subparsers(dest='action',required=True)
    imp=sub.add_parser('import'); imp.add_argument('jsonl',type=Path)
    sub.add_parser('status')
    args=parser.parse_args()
    try:
        runs, skipped = read_runs(args.jsonl) if args.action=='import' else ([],0)
        db=connect(DB_PATH)
        try:
            result=summary(db) if args.action=='status' else dict(scope='local_lab_only',**ingest(db,runs),missing_results=skipped)
        finally:
            db.close()
        print(json.dumps(result,indent=2,allow_nan=False)); return 0
    except (OSError,ValueError,TypeError,KeyError,OverflowError,sqlite3.Error) as exc:
        print(f'Evidence operation stopped: {exc}',file=sys.stderr); return 1


if __name__=='__main__':
    raise SystemExit(main())
