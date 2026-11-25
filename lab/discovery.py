"""Read-only, bounded HTML discovery for the local GhostLead Lab only."""
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
import http.client
import json
import re
import time
from urllib.parse import urljoin, urlsplit

HOST = '127.0.0.1'
PORT = 5501
MAX_PAGES = 20
MAX_BYTES = 256 * 1024
MAX_SECONDS = 25
MAX_LINKS = 200


def origin():
    return f'http://{HOST}:{PORT}'


def local_path(base, raw):
    if not raw or len(raw) > 1024 or any(ord(c) < 32 or c == '\\' for c in raw):
        return None
    try:
        u = urlsplit(urljoin(origin() + base, raw))
        if (u.scheme != 'http' or u.netloc != f'{HOST}:{PORT}' or u.query
                or not re.fullmatch(r'/[A-Za-z0-9_./-]*', u.path or '/')):
            return None
        p = u.path or '/'
        if '//' in p or any(s in {'.', '..'} for s in p.split('/')):
            return None
        return p
    except ValueError:
        return None


class Structure(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.links = set()
        self.skipped = 0
        self.forms = []
        self.form = None
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'a' and 'href' in a:
            p = local_path(self.path, a['href'])
            if p is not None and len(self.links) < MAX_LINKS: self.links.add(p)
            else: self.skipped += 1
        if tag == 'form' and len(self.forms) < 30:
            action = local_path(self.path, a.get('action') or self.path)
            self.form = {'action': action, 'method': (a.get('method') or 'get').upper()[:16], 'fields': []}
            self.forms.append(self.form)
        if tag in {'input','select','textarea','button'} and self.form is not None and len(self.form['fields']) < 100:
            self.form['fields'].append({'name': (a.get('name') or '')[:100], 'type': (a.get('type') or ('text' if tag == 'input' else tag))[:32], 'required': 'required' in a})

    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
        if tag == 'form': self.form = None

    def handle_data(self, data):
        if self.in_title: self.title = (self.title + data)[:160]


def fetch(path, deadline):
    """Connect directly to the literal loopback address; no proxies or redirects."""
    if local_path('/', path) != path:
        raise ValueError('Invalid local path')
    remaining = deadline - time.monotonic()
    if remaining <= 0: raise TimeoutError('Discovery time budget exhausted')
    conn = http.client.HTTPConnection(HOST, PORT, timeout=min(4, remaining))
    started = time.monotonic()
    try:
        conn.request('GET', path, headers={'Accept': 'text/html, application/json', 'Connection': 'close'})
        r = conn.getresponse()
        if 300 <= r.status < 400:
            return r.status, '', b'', round((time.monotonic()-started)*1000), 'redirect_not_followed'
        kind = (r.getheader('Content-Type') or '').split(';')[0].lower()
        data = bytearray()
        while len(data) <= MAX_BYTES:
            if time.monotonic() >= deadline: raise TimeoutError('Discovery time budget exhausted')
            # read1 returns available data rather than waiting to fill the entire buffer.
            chunk = r.read1(min(8192, MAX_BYTES + 1 - len(data)))
            if not chunk: break
            data.extend(chunk)
        elapsed = round((time.monotonic()-started)*1000)
        if len(data) > MAX_BYTES: return r.status, kind, b'', elapsed, 'response_too_large'
        return r.status, kind, bytes(data), elapsed, None
    finally:
        conn.close()


def discover():
    start = time.monotonic()
    deadline = start + MAX_SECONDS
    status, kind, body, _, error = fetch('/api/health', deadline)
    if error or status != 200 or kind != 'application/json': raise RuntimeError('GhostLead Lab identity check failed')
    try: identity = json.loads(body)
    except (ValueError, UnicodeError) as exc: raise RuntimeError('GhostLead Lab identity check failed') from exc
    if identity != {'service':'ghostlead-lab','status':'ok','synthetic':True}:
        raise RuntimeError('GhostLead Lab identity check failed')
    queue = deque(['/'])
    seen = {'/'}
    pages = []
    skipped = set()
    while queue and len(pages) < MAX_PAGES and time.monotonic() < deadline:
        path = queue.popleft()
        item = {'path':path,'status':None,'elapsed_ms':None,'title':'','links':[],'forms':[],'error':None}
        try:
            status, kind, body, elapsed, error = fetch(path, deadline)
            item.update(status=status, elapsed_ms=elapsed, error=error)
            if kind == 'text/html' and not error:
                parser = Structure(path)
                parser.feed(body.decode('utf-8', errors='replace'))
                parser.close()
                item.update(title=parser.title, links=sorted(parser.links), forms=parser.forms, excluded_links=parser.skipped)
                for p in item['links']:
                    if p.startswith('/api/') or p == '/api':
                        skipped.add(p)  # API data and submission endpoints are not crawled.
                    elif p not in seen and len(seen) < MAX_LINKS:
                        seen.add(p); queue.append(p)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            item['error'] = type(exc).__name__
        pages.append(item)
    return {'schema_version':1,'scope':'local_lab_only','origin':origin(),'observed_at':datetime.now(timezone.utc).isoformat(),
            'pages':pages,'skipped_api_paths':sorted(skipped),'truncated':bool(queue) or len(seen)>=MAX_LINKS,
            'summary':{'pages':len(pages),'forms':sum(len(p['forms']) for p in pages),'http_errors':sum(p['status'] is not None and p['status']>=400 for p in pages),
                       'request_errors':sum(bool(p['error']) for p in pages)}}


def main():
    import sys
    if len(sys.argv) != 1:
        print('Usage: python -m lab.discovery (no target arguments accepted)', file=sys.stderr); return 2
    try: print(json.dumps(discover(), indent=2)); return 0
    except (OSError, http.client.HTTPException, RuntimeError, ValueError) as exc:
        print(f'Discovery stopped: {exc}. Start GhostLead Lab first.', file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
