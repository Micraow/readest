"""Fetch only the three preregistered public works; never accepts input URLs."""
import hashlib
import json
from pathlib import Path
import urllib.request

base = Path(__file__).resolve().parent
manifest = json.loads((base / 'manifest.json').read_text())
output = base / 'inputs'
output.mkdir(exist_ok=True)
for source in manifest['sources']:
    url = source['url']
    assert url.startswith('https://arxiv.org/pdf/') and 'v' in url.rsplit('/', 1)[-1]
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(12 * 1024 * 1024 + 1)
    if len(data) > 12 * 1024 * 1024 or not data.startswith(b'%PDF-'):
        raise RuntimeError('Invalid or oversized public PDF: ' + source['key'])
    digest = hashlib.sha256(data).hexdigest()
    if digest != source['sha256']:
        raise RuntimeError(f"Public source hash mismatch: {source['key']} {digest}")
    (output / (source['key'] + '.pdf')).write_bytes(data)
    print(source['key'], len(data), digest, flush=True)
