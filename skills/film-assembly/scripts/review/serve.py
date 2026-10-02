# Review server for a cut folder: serves index.html (player + timecoded notes), the video with
# HTTP Range support (plain `python -m http.server` can't seek), and a notes API.
#   cp index.html serve.py <cut-dir>/ && cd <cut-dir> && python3 serve.py 8765
#   open http://localhost:8765/?cut=<cut>   (forward the port when the cut dir is remote)
# Notes land in <cut-dir>/notes/<cut>.json and <cut>.md.
import http.server, json, os, re, sys, time

NOTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notes')

def tc(t):
    return f'{int(t // 60):02d}:{t % 60:04.1f}'

class H(http.server.SimpleHTTPRequestHandler):
    def _cut(self):
        m = re.fullmatch(r'/api/notes/([\w.-]+)', self.path.split('?')[0])
        return m and m[1]

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        cut = self._cut()
        if not cut:
            return super().do_GET()
        p = os.path.join(NOTES, cut + '.json')
        self._json(200, json.load(open(p)) if os.path.exists(p) else [])

    def do_POST(self):
        cut = self._cut()
        if not cut:
            return self._json(404, {'error': 'not found'})
        notes = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        notes.sort(key=lambda n: n['t'])
        os.makedirs(NOTES, exist_ok=True)
        base = os.path.join(NOTES, cut)
        with open(base + '.json.tmp', 'w') as f:
            json.dump(notes, f, ensure_ascii=False, indent=1)
        os.replace(base + '.json.tmp', base + '.json')
        with open(base + '.md', 'w') as f:
            f.write(f'# {cut} 批注 ({len(notes)})\n\n')
            for n in notes:
                sub = f'  〔字幕: {n["sub"]}〕' if n.get('sub') else ''
                f.write(f'- **{tc(n["t"])}** ({n["t"]:.2f}s) {n["text"]}{sub}\n')
        self._json(200, {'ok': True, 'n': len(notes), 'saved': time.strftime('%H:%M:%S')})

    def end_headers(self):
        if self.path.endswith(('.html', '/')):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        if not m or not os.path.isfile(path):
            self._left = None
            return super().send_head()
        size = os.path.getsize(path)
        a = int(m[1]) if m[1] else size - int(m[2])
        b = int(m[2]) if m[1] and m[2] else size - 1
        b = min(b, size - 1)
        f = open(path, 'rb'); f.seek(a)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
        self.send_header('Content-Length', str(b - a + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        self._left = b - a + 1
        return f

    def copyfile(self, src, dst):
        left = getattr(self, '_left', None)
        if left is None:
            return super().copyfile(src, dst)
        while left > 0:
            buf = src.read(min(1 << 20, left))
            if not buf: break
            try: dst.write(buf)
            except (BrokenPipeError, ConnectionResetError): break
            left -= len(buf)

H.extensions_map.update({'.vtt': 'text/vtt', '.webm': 'video/webm', '.mp4': 'video/mp4'})
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
