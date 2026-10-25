"""Labelled stateless routing/SSE laboratory; never a Pi or model replica."""
import http.server,json,os,socket,threading,time,urllib.parse
from pathlib import Path
backend=os.environ['BACKEND_ID'];ledger=Path(os.environ['EVIDENCE_FILE']);lock=threading.Lock();gates={};failed=False

def record(kind,rid,**kw):
    with lock:
        with ledger.open('a') as f:f.write(json.dumps({'at_ns':time.time_ns(),'backend':backend,'kind':kind,'id':rid,**kw})+'\n');f.flush();os.fsync(f.fileno())

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def reply(self,status,data):
        raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):self.do_GET()
    def do_GET(self):
        global failed
        parsed=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(parsed.query);rid=self.headers.get('X-Request-ID') or q.get('id',[''])[0]
        if self.path.startswith('/control/release'):
            record('release',rid);gates.setdefault(rid,threading.Event()).set();self.reply(200,{'released':rid});return
        if self.path.startswith('/control/fail'):
            failed=q.get('enabled',['1'])[0]=='1';self.reply(200,{'failed':failed});return
        if self.path.startswith('/control/ledger'):
            self.reply(200,[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []);return
        record('received',rid,path=self.path,method=self.command)
        if self.path.startswith('/drop'):
            self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
        if failed:self.reply(503,{'backend':backend,'id':rid,'synthetic_fault':True});return
        if parsed.path=='/stream':
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            try:
                self.wfile.write(('event: marker\ndata: '+json.dumps({'id':rid,'backend':backend})+'\n\n').encode());self.wfile.flush();record('marker',rid)
                if not gates.setdefault(rid,threading.Event()).wait(8):record('watchdog',rid);return
                self.wfile.write(('event: terminal\ndata: '+json.dumps({'id':rid,'backend':backend})+'\n\n').encode());self.wfile.flush();record('terminal',rid)
            except (BrokenPipeError,ConnectionResetError):record('disconnect',rid)
            self.close_connection=True;return
        if parsed.path=='/truncate':
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length','9999');self.end_headers();self.wfile.write(b'event: marker\ndata: partial\n\n');self.wfile.flush();self.close_connection=True;return
        self.reply(200,{'backend':backend,'id':rid,'kind':'stateless synthetic routing fixture'})

http.server.ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
