"""Run only inside the GROBID --network none namespace. No third-party requests."""
import hashlib
import json
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIELDS = [(name, '0') for name in ('consolidateHeader', 'consolidateCitations', 'consolidateFunders')]
FIELDS += [(name, '1') for name in ('includeRawCitations', 'includeRawAffiliations', 'includeRawCopyrights', 'generateIDs')]
FIELDS += [('segmentSentences', '0')]
FIELDS += [('teiCoordinates', tag) for tag in ('persName', 'figure', 'ref', 'biblStruct', 'formula', 'head', 'p', 'note', 'title', 'affiliation')]


def multipart(data, filename):
    boundary = 'grobid-public-diagnostic-fixed-boundary-20261008'
    parts = []
    for key, value in FIELDS:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="input"; filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'.encode())
    return boundary, b''.join(parts) + data + f'\r\n--{boundary}--\r\n'.encode()


def main():
    output = BASE / 'evidence'
    output.mkdir(exist_ok=True)
    manifest = json.loads((BASE / 'manifest.json').read_text())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    ready_started = time.monotonic()
    for attempt in range(90):
        try:
            with opener.open('http://127.0.0.1:8070/api/isalive', timeout=2) as response:
                if response.status == 200:
                    break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        (output / 'readiness.json').write_text(json.dumps({'ready': False, 'seconds': round(time.monotonic() - ready_started, 3)}))
        raise RuntimeError('GROBID did not become ready in 90 seconds')
    (output / 'readiness.json').write_text(json.dumps({'ready': True, 'seconds': round(time.monotonic() - ready_started, 3)}))
    status = []
    for source in manifest['sources']:
        dest = output / source['key']
        dest.mkdir(exist_ok=True)
        data = (BASE / 'inputs' / (source['key'] + '.pdf')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source['sha256']
        (dest / 'original.pdf').write_bytes(data)
        boundary, body = multipart(data, source['key'] + '.pdf')
        request = urllib.request.Request('http://127.0.0.1:8070/api/processFulltextDocument', data=body,
            headers={'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Accept': 'application/xml'})
        row = {'key': source['key'], 'sha256': source['sha256'], 'fields': FIELDS,
               'processing_scope': 'whole original PDF; no start/end cropping'}
        started = time.monotonic()
        status.append(row)
        row['state'] = 'in_progress'
        (output / 'requests.json').write_text(json.dumps(status, indent=2) + '\n')
        try:
            with opener.open(request, timeout=180) as response:
                raw = response.read(32 * 1024 * 1024 + 1)
                row['http_status'] = response.status
            if len(raw) > 32 * 1024 * 1024:
                raise RuntimeError('Oversized response')
            (dest / 'raw.tei.xml').write_bytes(raw)
            root = ET.fromstring(raw)
            assert root.tag.endswith('}TEI'), 'Expected a TEI root'
            row['tei_surfaces'] = len(root.findall('.//{http://www.tei-c.org/ns/1.0}surface'))
            row['ok'] = True
        except Exception as error:
            row.update(ok=False, error=f'{type(error).__name__}: {error}')
        row['seconds'] = round(time.monotonic() - started, 3)
        row['state'] = 'completed' if row['ok'] else 'failed'
        (output / 'requests.json').write_text(json.dumps(status, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    if not all(row['ok'] for row in status):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
