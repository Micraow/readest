"""Expose proposals and independent source evidence. Never repair or accept TEI."""
import hashlib
import html
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

NS = '{http://www.tei-c.org/ns/1.0}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
TAGS = {'p', 'head', 'title', 'persName', 'affiliation', 'figure', 'figDesc', 'table', 'formula', 'ref', 'biblStruct', 'note'}
COLORS = {'p': (0.1, 0.45, 0.8), 'figure': (0.8, 0.1, 0.2), 'formula': (0.6, 0.15, 0.8), 'persName': (0, 0.5, 0.25), 'head': (0.8, 0.45, 0)}


def coordinates(raw):
    result = []
    for part in raw.split(';') if raw else []:
        values = [float(value) for value in part.split(',')]
        if len(values) != 5 or not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid coordinates: ' + part)
        page, x, y, w, h = values
        if page < 1 or int(page) != page or w < 0 or h < 0:
            raise ValueError('Invalid rectangle: ' + part)
        result.append({'page': int(page), 'x': x, 'y': y, 'w': w, 'h': h})
    return result


def extract(raw):
    root = ET.fromstring(raw)
    parent = {child: element for element in root.iter() for child in element}
    elements = [e for e in root.iter() if e.tag.removeprefix(NS) in TAGS]
    ids = {e: e.get(XML_ID, 'node-' + str(i + 1)) for i, e in enumerate(elements)}
    nodes, relations = [], []
    actual_ids = {e.get(XML_ID) for e in root.iter() if e.get(XML_ID)}
    for order, e in enumerate(elements):
        tag = e.tag.removeprefix(NS)
        ancestors, a = [], parent.get(e)
        while a is not None:
            ancestors.append(a)
            a = parent.get(a)
        scope = next((a.tag.removeprefix(NS) for a in ancestors if a.tag in {NS + 'teiHeader', NS + 'body', NS + 'back', NS + 'abstract'}), 'other')
        owner = next((a for a in ancestors if a in ids), None)
        node = {'id': ids[e], 'tag': tag, 'type': e.get('type'), 'order': order, 'scope': scope,
                'text': ''.join(e.itertext()).strip(), 'coords': coordinates(e.get('coords', '')),
                'teiAttributes': dict(e.attrib), 'parent': ids.get(owner)}
        # Keep individual source rectangles; do not make one large crop envelope.
        if tag == 'figDesc' and not node['coords']:
            figure = next((a for a in ancestors if a.tag == NS + 'figure'), None)
            node['figureEnvelopeForReviewOnly'] = coordinates(figure.get('coords', '')) if figure is not None else []
        nodes.append(node)
        if owner is not None:
            relations.append({'from': ids[e], 'to': ids[owner], 'relation': 'contained-in'})
        if tag == 'figDesc':
            figure = next((a for a in ancestors if a.tag == NS + 'figure'), None)
            if figure is not None:
                relations.append({'from': ids[e], 'to': ids[figure], 'relation': 'caption-of'})
        if tag == 'ref':
            for target in e.get('target', '').split():
                target_id = target.removeprefix('#')
                relations.append({'from': ids[e], 'to': target_id, 'relation': 'refers-to', 'resolved': target_id in actual_ids})
    body = [n for n in nodes if n['scope'] == 'body' and n['tag'] in {'p', 'head', 'formula'} and
            not any(a.tag in {NS+'figure', NS+'table', NS+'note'} for a in _ancestors(elements[n['order']], parent))]
    for left, right in zip(body, body[1:]):
        relations.append({'from': left['id'], 'to': right['id'], 'relation': 'next-in-TEI-body-order', 'not_verified': True})
    return root, nodes, relations


def _ancestors(element, parents):
    element = parents.get(element)
    while element is not None:
        yield element
        element = parents.get(element)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    import fitz
    base = Path(__file__).resolve().parent
    manifest = json.loads((base/'manifest.json').read_text())
    summaries = []
    for source in manifest['sources']:
        dest = base/'evidence'/source['key']
        original = base/'inputs'/(source['key']+'.pdf')
        if not original.exists():
            continue
        data = original.read_bytes()
        assert hashlib.sha256(data).hexdigest() == source['sha256']
        dest.mkdir(exist_ok=True)
        (dest/'original.pdf').write_bytes(data)
        doc = fitz.open(stream=data, filetype='pdf')
        if not (dest/'raw.tei.xml').exists():
            summaries.append({'key':source['key'],'error':'No raw TEI; original preserved','native_pages':len(doc)})
            continue
        root, nodes, relations = extract((dest/'raw.tei.xml').read_bytes())
        dump(dest/'structure-proposals.json', {'nodes':nodes,'relations':relations})
        native = []
        for number, page in enumerate(doc, 1):
            native.append({'page':number,'rect':list(page.rect),'cropbox':list(page.cropbox),
                'mediabox':list(page.mediabox),'rotation':page.rotation,
                'words':page.get_text('words',sort=False),
                'raw_text_chars':page.get_text('rawdict', flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)})
        dump(dest/'native-evidence.json', native)
        surfaces = {int(e.get('n')): [float(e.get('lrx')),float(e.get('lry'))] for e in root.iter(NS+'surface')}
        # Review header plus neighbors, without changing which diagnostic pages were preregistered.
        pages = sorted({1} | {p for n in source['pages'] for p in (n-1,n,n+1) if 1<=p<=len(doc)})
        page_reports=[]
        for number in pages:
            page=doc[number-1]
            d=dest/f'page-{number:02}'
            d.mkdir(exist_ok=True)
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(d/'source.png')
            selected=[n for n in nodes if any(c['page']==number for c in n['coords']+n.get('figureEnvelopeForReviewOnly',[]))]
            dump(d/'nodes-in-TEI-order.json',selected)
            size=surfaces.get(number)
            aligned=bool(size and abs(size[0]-page.rect.width)<0.2 and abs(size[1]-page.rect.height)<0.2 and page.rotation==0)
            overlay=fitz.open(stream=data,filetype='pdf')
            canvas=overlay[number-1]
            if aligned:
                for n in selected:
                    if n['tag'] in {'ref','title','affiliation','biblStruct','figDesc'}:
                        continue
                    for c in n['coords']:
                        if c['page']!=number:continue
                        rect=fitz.Rect(c['x'],c['y'],c['x']+c['w'],c['y']+c['h'])
                        if rect.is_empty or not rect.intersects(canvas.rect):continue
                        color=COLORS.get(n['tag'],(0.3,0.3,0.3))
                        canvas.draw_rect(rect,color=color,width=0.6)
                canvas.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(d/'overlay.png')
            overlay.close()
            pieces=['<!doctype html><meta charset="utf-8"><title>Structure review</title><style>body{font:16px sans-serif;max-width:1450px;margin:auto}img{max-width:48%}pre{white-space:pre-wrap}article{border-top:1px solid #ccc;padding:12px}</style>',
                f'<h1>{html.escape(source["key"])} page {number}</h1><p>Proposals only. Formula strings are NOT faithful math. Original and overlay remain independently visible. Coordinate alignment: {aligned}.</p>',
                '<img src="source.png" alt="Original PDF page">' + ('<img src="overlay.png" alt="TEI proposal rectangles">' if aligned else '')]
            for n in selected:
                pieces.append(f'<article><b>{html.escape(n["id"])} · {n["tag"]} · {n["scope"]}</b><pre>{html.escape(n["text"])}</pre><small>{html.escape(json.dumps(n["coords"]))}</small></article>')
            (d/'review.html').write_text('\n'.join(pieces))
            page_reports.append({'page':number,'diagnostic':number in source['pages'],'coordinate_frame_checked':aligned,'node_ids':[n['id'] for n in selected]})
        cross_page=[{'id':n['id'],'pages':sorted({c['page'] for c in n['coords']}),'text':n['text']} for n in nodes
            if n['tag']=='p' and len({c['page'] for c in n['coords']})>1]
        authors=[n for n in nodes if n['tag']=='persName' and n['scope']=='teiHeader']
        summary={'key':source['key'],'native_pages':len(doc),'tei_surfaces':len(surfaces),'review_pages':page_reports,
                 'header_authors':authors,'cross_page_paragraph_proposals':cross_page,
                 'unresolved_reference_proposals':[r for r in relations if r.get('resolved') is False],
                 'warning':'Counts and matching frames establish inspectability only, not structural correctness or coverage.'}
        dump(dest/'review-summary.json',summary)
        summaries.append(summary)
        doc.close()
    dump(base/'evidence'/'summary.json',summaries)
    print(json.dumps([{'key':s['key'],'native_pages':s['native_pages'],'tei_surfaces':s.get('tei_surfaces'),'authors':len(s.get('header_authors',[]))} for s in summaries]))


if __name__=='__main__':
    main()
