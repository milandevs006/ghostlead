"""Local-only, in-memory synthetic website for GhostLead development."""
from collections import deque
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
from threading import Lock
from time import sleep
from urllib.parse import parse_qs, urlsplit

STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#152d49;font:16px/1.6 system-ui,sans-serif}header{background:#fff;border-bottom:1px solid #dce5f1}nav,main{max-width:1000px;margin:auto;padding:24px}nav{display:flex;align-items:center;gap:24px;flex-wrap:wrap}nav b{margin-right:auto}a{color:#245b97}main{padding-top:40px}h1{font-size:clamp(30px,5vw,48px);line-height:1.1;letter-spacing:-1.6px}h2{font-size:20px}.tag{display:inline-block;background:#e5edf8;color:#244b78;border-radius:40px;padding:6px 14px;font-size:12px;font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:24px 0}.card{background:#fff;border:1px solid #dce5f1;padding:24px;border-radius:16px}label{display:block;font-weight:600;margin:16px 0 8px}input,select,button{font:inherit;padding:12px;border:1px solid #b9cde3;border-radius:8px;width:100%;background:#fff;color:#152d49}button{background:#244b78;color:#fff;border:0;cursor:pointer;margin-top:20px}small{color:#536b87}.primary{display:inline-block;padding:12px 18px;border-radius:8px;background:#244b78;color:white;text-decoration:none}code{overflow-wrap:anywhere}footer{max-width:1000px;margin:auto;padding:24px;color:#536b87;font-size:13px}
"""

def page(title, content):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)} | GhostLead Lab</title><style>{STYLE}</style></head>'
            '<body><header><nav><b>ghostlead. / LAB</b><a href="/">Home</a>'
            '<a href="/pricing">Pricing</a><a href="/contact">Contact</a>'
            '<a href="/lab/results">Lab results</a></nav></header><main>'
            '<span class="tag">LOCAL FIXTURE · SYNTHETIC DATA ONLY</span>'
            f'{content}</main><footer>Isolated development fixture. No real customer data, external services, or GhostLead database.</footer></body></html>')

class LabServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port=5501):
        super().__init__(("127.0.0.1", port), Handler)
        self.token = secrets.token_urlsafe(24)
        self.events = deque(maxlen=100)
        self.lock = Lock()

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def _allowed(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def _send(self, status, body, kind='text/html; charset=utf-8'):
        if isinstance(body, str): body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError): pass

    def _json(self, status, value):
        self._send(status, json.dumps(value, indent=2), 'application/json; charset=utf-8')

    def _error(self, status, message):
        self._send(status, page(str(status), f'<h1>{status}</h1><p>{escape(message)}</p><a href="/">Return home</a>'))

    def do_GET(self):
        if not self._allowed(): return self._error(403, 'Use the exact local loopback URL.')
        if not self.path.startswith('/') or self.path.startswith('//'): return self._error(400, 'Invalid path.')
        path = urlsplit(self.path).path
        if path == '/':
            self._send(200, page('Home', '<h1>Test every step.<br>Trust every result.</h1><p>A controlled website for testing lead journeys, response times and failure detection.</p><a class="primary" href="/contact">Try a test enquiry</a><div class="grid"><div class="card"><h2>Healthy page</h2><p>Normal response.</p><a href="/pricing">View pricing</a></div><div class="card"><h2>Broken link</h2><p>Returns HTTP 404 on purpose.</p><a href="/broken">Open broken link</a></div><div class="card"><h2>Slow response</h2><p>Controlled delay of 2 seconds.</p><a href="/slow">Open slow page</a></div><div class="card"><h2>Service error</h2><p>Returns HTTP 503 on purpose.</p><a href="/unavailable">Open unavailable page</a></div></div>'))
        elif path == '/pricing':
            self._send(200, page('Pricing', '<h1>Explore the test product.</h1><div class="card"><h2>Fixture plan</h2><p>No real pricing, payment or purchase.</p><a class="primary" href="/contact">Request a test enquiry</a></div>'))
        elif path == '/contact':
            self._send(200, page('Contact', f'<h1>Simulate an enquiry.</h1><p>Use only a synthetic ID beginning with test-. Do not enter personal data.</p><form class="card" action="/api/enquiry" method="post"><input type="hidden" name="token" value="{self.server.token}"><label for="id">Synthetic lead ID</label><input id="id" name="lead_id" required pattern="test-[A-Za-z0-9_-]{{1,40}}" placeholder="test-001" maxlength="45"><label for="scenario">Delivery scenario</label><select id="scenario" name="scenario"><option value="delivered">Successful delivery</option><option value="dropped">Accepted but not delivered</option><option value="rejected">Submission rejected</option></select><button>Submit test enquiry</button></form>'))
        elif path == '/slow':
            sleep(2)
            self._send(200, page('Slow page', '<h1>Slow response fixture</h1><p>Intentional two-second delay.</p>'))
        elif path == '/unavailable': self._error(503, 'Intentional service error.')
        elif path == '/api/health': self._json(200, {'service':'ghostlead-lab','status':'ok','synthetic':True})
        elif path == '/api/results':
            with self.server.lock: events = list(self.server.events)
            self._json(200, {'synthetic':True,'events':events})
        elif path == '/lab/results':
            with self.server.lock: events = list(self.server.events)
            rows = ''.join(f'<div class="card"><b>{escape(e["lead_id"])}</b><br>{escape(e["scenario"])} · source: {e["source"]} · destination: {e["destination"]}</div>' for e in reversed(events))
            self._send(200, page('Results', '<h1>Fixture results</h1><p>In memory only; cleared on restart. These are not GhostLead monitoring records.</p><a href="/api/results">View JSON</a><div class="grid">'+(rows or '<div class="card">No test submissions yet.</div>')+'</div>'))
        else: self._error(404, 'Page not found (intentional for /broken).')

    def do_POST(self):
        if not self._allowed(): return self._error(403, 'Invalid host.')
        origin = self.headers.get('Origin')
        if origin and origin != f'http://127.0.0.1:{self.server.server_port}': return self._error(403, 'Invalid origin.')
        if self.path != '/api/enquiry': return self._error(404, 'Unknown endpoint.')
        if self.headers.get_content_type() != 'application/x-www-form-urlencoded': return self._error(415, 'Form encoding required.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048: return self._error(413, 'Invalid form size.')
            fields = parse_qs(self.rfile.read(length).decode('utf-8'), strict_parsing=True, max_num_fields=3)
            if set(fields) != {'token','lead_id','scenario'} or any(len(v)!=1 for v in fields.values()): raise ValueError()
            token, lead, scenario = (fields[k][0] for k in ('token','lead_id','scenario'))
        except (ValueError, UnicodeError, TimeoutError): return self._error(400, 'Invalid form.')
        if not secrets.compare_digest(token.encode('utf-8'), self.server.token.encode('ascii')): return self._error(403, 'Invalid form token.')
        if not re.fullmatch(r'test-[A-Za-z0-9_-]{1,40}', lead) or scenario not in {'delivered','dropped','rejected'}: return self._error(400, 'Use a synthetic ID and supported scenario.')
        event = {'lead_id':lead,'scenario':scenario,'source':scenario!='rejected','destination':scenario=='delivered'}
        with self.server.lock: self.server.events.append(event)
        if scenario == 'rejected': return self._error(422, 'Intentional rejection; no source or destination event.')
        self._send(200, page('Received', '<h1>Test enquiry accepted</h1><p>Inspect the fixture results to see whether delivery occurred.</p><a href="/lab/results">View results</a>'))

if __name__ == '__main__':
    with LabServer() as server:
        print('GhostLead Lab: http://127.0.0.1:5501 — local only; Ctrl+C to stop', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
