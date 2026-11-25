"""Analyse real observations from the fixed local GhostLead Lab discovery runner."""
import argparse
import html
import json
import math
import statistics
import sys
from . import discovery

SLOW_MS = 1000


def percentile(values, p):
    """Linear interpolation between adjacent sorted observations."""
    if not values:
        return None
    v = sorted(values)
    k = (len(v)-1)*p
    lo, hi = math.floor(k), math.ceil(k)
    return round(v[lo]+(v[hi]-v[lo])*(k-lo), 1)


def analyse(report):
    if report.get('scope') != 'local_lab_only' or report.get('origin') != discovery.origin() or report.get('schema_version') != 1:
        raise ValueError('Only local GhostLead Lab discovery observations are accepted')
    pages = report['pages']
    incoming = {}
    for page in pages:
        for link in page['links']:
            incoming.setdefault(link, set()).add(page['path'])
    results = []
    findings = []
    times = []
    for page in pages:
        status, elapsed, error = page['status'], page['elapsed_ms'], page['error']
        refs = sorted(incoming.get(page['path'], set()))
        if status in (404, 410):
            category, severity = ('broken_link' if refs else 'missing_page'), 'high'
        elif status is not None and 500 <= status <= 599:
            category, severity = 'server_error', 'high'
        elif status is not None and 300 <= status <= 399:
            category, severity = 'redirect_unchecked', 'info'
        elif error or status is None:
            category, severity = 'incomplete', 'warning'
        elif 400 <= status <= 499:
            category, severity = 'client_error', 'warning'
        elif 200 <= status <= 299:
            if type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed >= 0:
                times.append(elapsed)
                category, severity = ('slow', 'warning') if elapsed >= SLOW_MS else ('healthy', 'none')
            else:
                category, severity = 'incomplete', 'warning'
        else:
            category, severity = 'incomplete', 'warning'
        result = {'path':page['path'], 'status':status, 'elapsed_ms':elapsed,
                  'category':category,'severity':severity,'referrers':refs,'error':error}
        results.append(result)
        if category != 'healthy': findings.append(result.copy())
    findings.sort(key=lambda x: ({'high':0,'warning':1,'info':2}[x['severity']],x['path']))
    counts = {k:sum(r['category']==k for r in results) for k in ('healthy','slow','broken_link','missing_page','server_error','client_error','redirect_unchecked','incomplete')}
    return {'schema_version':1,'scope':'local_lab_only','origin':report['origin'],'observed_at':report['observed_at'],
            'truncated':report['truncated'],'slow_threshold_ms':SLOW_MS,'pages':results,'findings':findings,
            'summary':{'pages':len(results),'findings':len(findings),**counts},
            'latency_ms':{'sample_count':len(times),'min':min(times) if times else None,
                          'median':statistics.median(times) if times else None,'p95':percentile(times,.95),
                          'max':max(times) if times else None}}


def render_html(report):
    """Static escaped report, no scripts, remote assets or network requests."""
    def esc(value): return html.escape('—' if value is None else str(value), quote=True)
    s=report['summary']; latency=report['latency_ms']
    cards=''.join(f'<article><small>{esc(label)}</small><strong>{esc(value)}</strong></article>' for label,value in [
        ('Pages observed',s['pages']),('Broken links',s['broken_link']),('Server errors',s['server_error']),('Slow pages',s['slow']),('Median (ms)',latency['median']),('P95 (ms)',latency['p95'])])
    rows=''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in (p['path'],p['status'],p['elapsed_ms'],p['category'],p['severity'],', '.join(p['referrers']),p['error']))+'</tr>' for p in report['pages'])
    findings=''.join(f'<li><b>{esc(p["category"])}</b> — {esc(p["path"])} ({esc(p["severity"])})</li>' for p in report['findings']) or '<li>No findings among observed pages.</li>'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GhostLead Lab | Performance report</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fb;color:#182c45;font:16px system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:32px}}header{{border-bottom:1px solid #cddbeb;padding-bottom:20px}}h1{{font-size:clamp(26px,5vw,42px);margin:8px 0}}small,p{{color:#526780}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:24px 0}}article,section{{background:#fff;border:1px solid #dce4ed;border-radius:14px;padding:20px}}strong{{display:block;font-size:30px;color:#244b78;margin-top:10px}}section{{margin:16px 0;overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e5ebf3;overflow-wrap:anywhere}}th{{background:#edf3fa}}li{{padding:8px}}.note{{background:#e5edf8;padding:12px;border-radius:8px}}</style>
<main><header><small>GHOSTLEAD / LAB INTELLIGENCE / ALPHA.6</small><h1>Broken link &amp; performance report</h1><p>Observed {esc(report['observed_at'])} · {esc(report['origin'])}</p><p class="note">Controlled lab only · {esc('Incomplete discovery coverage' if report['truncated'] else 'Discovery queue exhausted within configured limits')} · No external monitoring</p></header><div class="cards">{cards}</div><section><h2>Findings</h2><ul>{findings}</ul></section><section><h2>Page observations</h2><table><thead><tr><th>Path</th><th>HTTP</th><th>Elapsed ms</th><th>Classification</th><th>Severity</th><th>Referring pages</th><th>Error</th></tr></thead><tbody>{rows}</tbody></table></section><p>Latency sample: {esc(latency['sample_count'])} completed 2xx responses. Slow threshold: {SLOW_MS} ms. Elapsed HTTP request and bounded body read, not browser rendering, Core Web Vitals or an uptime SLA. Redirects are not followed. A finding is not proof of lost revenue.</p></main></html>'''


def main():
    parser=argparse.ArgumentParser(description='Analyse the fixed local GhostLead Lab; no target arguments.')
    parser.add_argument('--format', choices=('json','html'), default='json')
    args=parser.parse_args()
    try:
        report=analyse(discovery.discover())
        print(render_html(report) if args.format=='html' else json.dumps(report,indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, discovery.http.client.HTTPException) as exc:
        print(f'Analysis stopped: {exc}. Start GhostLead Lab first.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
