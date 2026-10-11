"""Loopback-only immutable enumerated session assets; no filesystem browsing."""
import argparse
import hashlib
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def frozen_routes(folder):
    folder=pathlib.Path(folder);config=json.loads((folder/'ASSET-ALLOWLIST.json').read_text());bodies={}
    for url,a in config['assets'].items():
        p=pathlib.PurePosixPath(a['path'])
        if p.is_absolute() or '..' in p.parts or not url.startswith(('/document/','/session-manifest.json')) or '?' in url or '..' in url:raise ValueError('invalid asset path')
        data=(folder/p).read_bytes()
        if len(data)!=a['bytes'] or hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('frozen asset pin differs')
        bodies[url]=(data,a['mime'])
    code=pathlib.Path(__file__).parent
    for name in ('paper_session.html','paper_app.mjs','paper_session.mjs','session_contract.mjs'):
        bodies['/qa' if name.endswith('.html') else '/'+name]=((code/name).read_bytes(),'text/html; charset=utf-8' if name.endswith('.html') else 'text/javascript; charset=utf-8')
    bodies['/']=bodies['/qa'];return bodies


def main():
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--port',type=int,default=8768);a=p.parse_args();bodies=frozen_routes(a.folder)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in bodies:return self.send_error(404)
            data,mime=bodies[self.path];self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; frame-src 'self' about:; object-src 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers();self.wfile.write(data)
    print(json.dumps(dict(loopback='127.0.0.1',port=a.port,files=len(bodies),manifest_sha256=hashlib.sha256(bodies['/session-manifest.json'][0]).hexdigest())),flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()

if __name__=='__main__':main()
