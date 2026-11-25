"""One bounded, read-only monitoring run against GhostLead Lab only."""
import argparse
from datetime import datetime, timezone
import json
import math
import subprocess
import sys
import time
import uuid
from . import analysis, discovery

WORKER_TIMEOUT_SECONDS = 32

class WorkerError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def discover_in_worker():
    # Fixed module, no shell or caller-provided target. Timeout kills/reaps worker.
    result = subprocess.run([sys.executable, '-m', 'lab.discovery'],
                            capture_output=True, timeout=WORKER_TIMEOUT_SECONDS,
                            check=False)
    if result.returncode != 0:
        raise WorkerError('discovery_failed')
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError) as exc:
        raise WorkerError('invalid_worker_output') from exc


def validate_observations(report):
    if (not isinstance(report, dict) or report.get('scope') != 'local_lab_only'
            or report.get('origin') != discovery.origin()
            or report.get('schema_version') != 1
            or type(report.get('truncated')) is not bool
            or not isinstance(report.get('observed_at'), str)
            or not isinstance(report.get('pages'), list)
            or not 1 <= len(report['pages']) <= discovery.MAX_PAGES):
        raise WorkerError('invalid_worker_output')
    paths = set()
    for page in report['pages']:
        if not isinstance(page, dict):
            raise WorkerError('invalid_worker_output')
        path, status, elapsed, error = (page.get(k) for k in ('path','status','elapsed_ms','error'))
        if (not isinstance(path, str) or discovery.local_path('/', path) != path
                or path in paths or path == '/api' or path.startswith('/api/')
                or not {'status','elapsed_ms','error','links'} <= page.keys()
                or (status is not None and (type(status) is not int or not 100 <= status <= 599))
                or (elapsed is not None and (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed < 0))
                or (error is not None and (not isinstance(error,str) or len(error)>80))
                or not isinstance(page['links'], list) or len(page['links']) > discovery.MAX_LINKS
                or any(not isinstance(link,str) or discovery.local_path(path,link)!=link for link in page['links'])):
            raise WorkerError('invalid_worker_output')
        paths.add(path)
    if '/' not in paths:
        raise WorkerError('invalid_worker_output')


def run_monitoring():
    """Return a fresh run envelope; execution is independent of observed health."""
    started = time.monotonic()
    result = {'schema_version':1,'run_id':str(uuid.uuid4()),'scope':'local_lab_only',
              'origin':discovery.origin(),'started_at':utc_now(),'finished_at':None,'duration_ms':None,
              'execution_status':'failed','observed_health':'unknown','coverage':'unknown',
              'error_code':None,'analysis':None}
    try:
        observations = discover_in_worker()
        validate_observations(observations)
        report = analysis.analyse(observations)
        s = report['summary']
        incomplete = (report['truncated'] or s['incomplete'] > 0 or s['redirect_unchecked'] > 0
                      or any(p['error'] for p in report['pages'])
                      or any(p.get('excluded_links',0) for p in observations['pages']))
        issues = any(s[k] > 0 for k in ('slow','broken_link','missing_page','server_error','client_error'))
        result.update(execution_status='partial' if incomplete else 'completed',
                      coverage='limited' if incomplete else 'observed_links_only',
                      observed_health='issues_detected' if issues else ('unknown' if incomplete else 'no_issues_observed'),
                      analysis=report)
    except subprocess.TimeoutExpired:
        result['error_code']='worker_timeout'
    except WorkerError as exc:
        result['error_code']=str(exc)
    except OSError:
        result['error_code']='worker_start_failed'
    except (ValueError,TypeError,KeyError,RuntimeError,OverflowError):
        result['error_code']='analysis_failed'
    finally:
        result['finished_at']=utc_now()
        result['duration_ms']=max(0,round((time.monotonic()-started)*1000))
    return result


def main():
    parser=argparse.ArgumentParser(description='Run one GhostLead Lab monitor; no target arguments.')
    parser.parse_args()
    report=run_monitoring()
    print(json.dumps(report,indent=2,allow_nan=False))
    return {'completed':0,'partial':2,'failed':1}[report['execution_status']]


if __name__=='__main__':
    raise SystemExit(main())
