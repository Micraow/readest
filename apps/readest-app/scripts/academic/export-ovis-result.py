"""Export a local Ovis page into Readest's result-import contract.

Accept reviewed adapter results or raw Ovis Markdown. No model inference runs.
Raw exports also write a provenance sidecar and local PDF crops for inspection.
"""
import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import tempfile

from ovis_markdown import adapt_blocks, figure_region, parse_blocks, without_code


def rect(bounds):
    x, y, right, bottom = bounds
    return {'x': x, 'y': y, 'width': right-x, 'height': bottom-y}


def measure_source_font_size(page, bounds):
    """Measure native PDF points, not crop height or recognized math semantics.

    RAWDICT span.size is the font size; a char bbox may include line leading.
    Select by character center so tight ink crops still include their glyphs,
    while nearby text in an intersecting span cannot affect the measurement.
    Each non-whitespace character gets one vote, independent of span splitting,
    font family and glyph area. The median must also be the largest size: a
    minority larger glyph could be either a main letter or an enlarged symbol.
    Leave that scale unknown instead of guessing which belongs to script text.
    """
    import fitz
    left, top, right, bottom = bounds
    sizes = []
    characters = []
    native = page.get_text('rawdict', flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
    for block in native['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                size = span['size']
                alpha, flags = span.get('alpha'), span.get('char_flags')
                if alpha == 0 or (flags is not None and not flags & 24):
                    continue
                for char in span['chars']:
                    if not char['c'].strip() or char.get('synthetic', False):
                        continue
                    x0, y0, x1, y1 = char['bbox']
                    if left <= (x0 + x1) / 2 <= right and top <= (y0 + y1) / 2 <= bottom:
                        # Ignoring unknown in-crop glyphs could turn a script
                        # size into the median of the remaining known glyphs.
                        if alpha is None or flags is None or not math.isfinite(size) or size <= 0:
                            return None
                        dx, dy = line['dir']
                        if (not math.isclose(abs(dx), 1, rel_tol=1e-5) or abs(dy) > 1e-5
                                or line.get('wmode', 0) != 0 or len(char['c']) != 1):
                            return None
                        sizes.append(size)
                        characters.append((tuple(char['origin']), ord(char['c']), size))
    if not sizes:
        return None
    sizes.sort()
    lower, upper = sizes[(len(sizes) - 1) // 2], sizes[len(sizes) // 2]
    # Only tolerate floating-point transform noise, not distinct font sizes.
    if not math.isclose(lower, upper, rel_tol=1e-5):
        return None
    median = lower + (upper - lower) / 2
    # The reader already floors the scale denominator at one PDF point. Do not
    # export a measurement that it cannot proportionally represent.
    if median < 1 or not math.isclose(median, sizes[-1], rel_tol=1e-5):
        return None
    # RAWDICT size uses sqrt(abs(det(text transform))); texttrace uses the
    # transformed writing-axis length. For horizontal text these must agree.
    # Unlike glyph height, this check survives PyMuPDF's bbox normalization for
    # fonts with ascender - descender < 1, without accepting nonuniform scales.
    traced = {}
    for span in page.get_texttrace():
        for codepoint, _, origin, _ in span['chars']:
            traced.setdefault(tuple(origin), []).append((codepoint, span['size']))
    for origin, codepoint, size in characters:
        matches = traced.get(origin, [])
        # A different/unmapped character at the same origin must not conceal
        # conflicting scale evidence. Still require a decoded match to align.
        if (not any(code == codepoint for code, _ in matches)
                or any(not math.isclose(size, other, rel_tol=1e-5) for _, other in matches)):
            return None
    return median


def export_result(pdf_path, page_number, result_dir, identity):
    import fitz
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    structure = json.loads((result_dir/'blocks.json').read_text())
    receipt = json.loads((result_dir/'receipt.json').read_text())
    math = json.loads((result_dir/'native-math.json').read_text())
    if math['pdf_sha256'] != sha or math['page_number'] != page_number:
        raise ValueError('Source PDF/page does not match the processed result')
    with fitz.open(pdf_path) as pdf:
        page = pdf[page_number-1]
        if page.rotation:
            raise ValueError('This exporter currently supports unrotated PDF pages only')
        width, height, count = page.rect.width, page.rect.height, len(pdf)
        bundle = bundle_from_blocks(sha, page_number, width, height, count, structure, receipt, identity)
        for block in bundle['pages'][0]['blocks']:
            if block.get('role') == 'equation':
                box = block['box']
                size = measure_source_font_size(page, [box['x'], box['y'],
                                                box['x'] + box['width'], box['y'] + box['height']])
                if size is not None:
                    block['sourceFontSize'] = size
    return bundle


def bundle_from_blocks(sha, page_number, width, height, count, structure, receipt, identity):
    prefix = f'ovis-{sha[:12]}-p{page_number}-'
    note_ids = {note['marker']: prefix+note['id'] for note in structure['notes']}
    first_calls = {}
    marker = re.compile(r'\$\s*\^\{(\d+|\\dagger|\\ddagger|\*)\}\s*\$')
    def references(text, block_id):
        # Do not interpret note-like text inside Markdown code spans/fences.
        visible = without_code(text)
        def replace(match):
            label=match.group(1)
            if label not in note_ids or not visible[match.start():match.end()].strip():return match.group()
            first_calls.setdefault(label,block_id)
            display=label.replace('\\dagger','†').replace('\\ddagger','‡')
            return f'[{display}](#{note_ids[label]})'
        return marker.sub(replace,text)
    figures={item['asset']:item for item in receipt['figure_groups']}
    formulas={pathlib.Path(item['source_crop']['path']).name:item for item in receipt['source_formula_replacements']}
    blocks=[]
    for block in structure['blocks']:
        block_id=prefix+block['id']
        if block['kind']=='figure':
            caption=references(block['caption'],block_id)
            if block['labels']:
                caption+='\n\n<details><summary>Recognized figure labels</summary>\n\n'+'\n\n'.join(references(label,block_id) for label in block['labels'])+'\n\n</details>'
            blocks.append({'id':block_id,'kind':'visual','role':'figure','box':rect(figures[block['asset']]['bbox']),'caption':caption})
        elif block['kind']=='image':
            left,top,right,bottom=block['bbox']
            blocks.append({'id':block_id,'kind':'visual','role':'figure','box':rect([left*width/1000,top*height/1000,right*width/1000,bottom*height/1000])})
        else:
            match=re.fullmatch(r'!\[Source equation\]\(assets/([a-z0-9-]+\.png)\)',block['markdown'])
            if match and match.group(1) in formulas:
                blocks.append({'id':block_id,'kind':'visual','role':'equation','box':rect(formulas[match.group(1)]['source_crop']['bbox'])})
            else:
                blocks.append({'id':block_id,'kind':'markdown','markdown':references(block['markdown'],block_id)})
    for note in structure['notes']:
        text=note['content'];label=note['marker']
        if label in first_calls:text+=f'\n\n[↩](#{first_calls[label]})'
        blocks.append({'id':note_ids[label],'kind':'footnote','marker':label.replace('\\dagger','†').replace('\\ddagger','‡'),'markdown':text})
    return {'format':'readest-ovis-reflow','version':1,'pdfSha256':sha,'pageCount':count,'identity':identity,'pages':[{'page':page_number,'width':width,'height':height,'blocks':blocks}]}


def validate_identity(identity):
    keys = {'modelSha256', 'projectorSha256', 'promptSha256', 'runtimeRevision', 'configuration'}
    if not isinstance(identity, dict) or set(identity) != keys:
        raise ValueError('Invalid identity: expected the complete Readest identity contract')
    for key in keys - {'configuration'}:
        length = 40 if key == 'runtimeRevision' else 64
        if not isinstance(identity[key], str) or not re.fullmatch(r'[a-f0-9]{' + str(length) + '}', identity[key]):
            raise ValueError('Invalid identity hash or runtime revision')
    config = identity['configuration']
    if not isinstance(config, dict) or any(
        not isinstance(key, str) or not isinstance(value, (str, bool, int, float))
        or (isinstance(value, (int, float)) and not math.isfinite(value))
        for key, value in config.items()
    ):
        raise ValueError('Invalid identity configuration: expected flat, finite values')


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def check_destination(path, sources):
    if path.resolve() in {source.resolve() for source in sources}:
        raise ValueError('Output must not overwrite a source input')
    if path.is_symlink() or (path.exists() and path.stat().st_nlink > 1):
        raise ValueError('Refusing to overwrite a linked output file')


def atomic_write(path, data, sources):
    check_destination(path, sources)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.readest-ovis-', delete=False) as stream:
            temporary = pathlib.Path(stream.name)
            stream.write(data)
        # Replacing a destination never follows its file symlink or changes the
        # bytes of another hardlink, even if one appeared after the check.
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_markdown(pdf_path, page_number, markdown_path, identity, assets_dir,
                    expected_pdf_sha256=None, expected_markdown_sha256=None, protected_paths=()):
    """Convert caller-bound raw output, retaining original math and model text."""
    import fitz
    sources = [pdf_path, markdown_path, *protected_paths]
    validate_identity(identity)
    pdf_bytes, raw = pdf_path.read_bytes(), markdown_path.read_bytes()
    pdf_sha, markdown_sha = hashlib.sha256(pdf_bytes).hexdigest(), hashlib.sha256(raw).hexdigest()
    for name, actual, expected in [('PDF', pdf_sha, expected_pdf_sha256),
                                   ('Markdown', markdown_sha, expected_markdown_sha256)]:
        if expected is not None and actual != expected:
            raise ValueError(f'{name} SHA-256 does not match the expected input')
    structure = adapt_blocks(parse_blocks(raw.decode('utf-8')))
    if not structure['blocks'] and not structure['notes']:
        raise ValueError('Ovis Markdown is empty')
    receipt = {'figure_groups': [], 'source_formula_replacements': []}
    crops = []
    with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
        if type(page_number) is not int or not 1 <= page_number <= len(pdf):
            raise ValueError('Source page must be a 1-based page within the PDF')
        page = pdf[page_number - 1]
        if page.rotation:
            raise ValueError('This exporter currently supports unrotated PDF pages only')
        width, height, count = page.rect.width, page.rect.height, len(pdf)
        prefix = f'ovis-{pdf_sha[:12]}-p{page_number}-'
        for block in structure['blocks']:
            if block['kind'] == 'figure':
                region = figure_region(page, block)
                images = block['images']
            elif block['kind'] == 'image':
                left, top, right, bottom = block['bbox']
                region = fitz.Rect(left * width / 1000, top * height / 1000,
                                   right * width / 1000, bottom * height / 1000)
                images = [block]
            else:
                continue
            if region == page.rect:
                raise ValueError('A whole-page image or figure union is not a reflow crop')
            asset = f'{assets_dir.name}/{prefix}{block["id"]}.png'
            block['asset'] = asset
            if block['kind'] == 'figure':
                receipt['figure_groups'].append({'asset': asset, 'bbox': list(region)})
            crops.append({
                'blockId': prefix + block['id'], 'asset': asset, 'box': rect(region),
                'modelBoxes': [image['bbox'] for image in images],
                'modelCoordinateSpace': 'normalized-0-1000',
                'sourceBlockIds': block.get('source_ids', [block['id']]), 'dpi': 144,
            })
        # Validate every crop before creating any asset. Images use only this PDF.
        for crop in crops:
            check_destination(assets_dir / pathlib.Path(crop['asset']).name, sources)
        for crop in crops:
            box = crop['box']
            region = fitz.Rect(box['x'], box['y'], box['x'] + box['width'], box['y'] + box['height'])
            png = page.get_pixmap(dpi=crop['dpi'], clip=region, alpha=False).tobytes('png')
            assets_dir.mkdir(parents=True, exist_ok=True)
            atomic_write(assets_dir / pathlib.Path(crop['asset']).name, png, sources)
            crop['sha256'] = hashlib.sha256(png).hexdigest()
        bundle = bundle_from_blocks(pdf_sha, page_number, width, height, count, structure, receipt, identity)
    provenance = {
        'format': 'readest-ovis-export-provenance', 'version': 1, 'mode': 'raw-markdown',
        'source': {'pdfSha256': pdf_sha, 'markdownSha256': markdown_sha,
                   'page': page_number, 'binding': 'caller-declared'},
        'identity': identity, 'bundleSha256': hashlib.sha256(json_bytes(bundle)).hexdigest(),
        'adapter': {'version': 'ovis-markdown-1', 'pymupdfVersion': fitz.VersionBind},
        'verification': {'nativeMathChecked': False, 'ocrAccuracyChecked': False,
                         'modelGeometryVerified': False, 'wholePageFallback': False},
        'crops': crops,
        'limitations': [
            'The caller declares which PDF/page produced this Markdown; hashes establish bytes, not that attribution.',
            'Image geometry comes from model bbox tokens. Crops are rendered from the supplied PDF, not validated against OCR.',
            'Model/runtime identity is caller-declared. No inference or native math/table verification runs.',
            'Recognized text, formulas and tables retain any OCR mistakes; no source replacements are invented.',
        ],
    }
    return bundle, provenance


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=pathlib.Path,required=True)
    parser.add_argument('--page',type=int,required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--result-dir', type=pathlib.Path, help='Reviewed blocks/receipt/native-math directory')
    source.add_argument('--markdown', type=pathlib.Path, help='Raw UTF-8 Ovis output; produces an audit sidecar')
    parser.add_argument('--identity',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--expected-pdf-sha256', help='Optional input integrity check in raw Markdown mode')
    parser.add_argument('--expected-markdown-sha256', help='Optional raw-byte integrity check in Markdown mode')
    args=parser.parse_args()
    if args.result_dir and (args.expected_pdf_sha256 or args.expected_markdown_sha256):
        parser.error('Expected hashes are for --markdown; --result-dir verifies its existing native-math receipt')
    inputs = [args.pdf, args.identity] + ([args.markdown] if args.markdown else
              [args.result_dir / name for name in ['blocks.json', 'receipt.json', 'native-math.json']])
    sidecar = args.output.with_suffix('.provenance.json')
    if any(path.resolve() in [args.output.resolve(), sidecar.resolve()] for path in inputs):
        parser.error('Output files must not overwrite source inputs')
    if args.markdown and sidecar == args.output:
        parser.error('Bundle output cannot use the .provenance.json suffix')
    try:
        check_destination(args.output, inputs)
        if args.markdown:
            check_destination(sidecar, inputs)
        identity_bytes = args.identity.read_bytes()
        identity = json.loads(identity_bytes.decode('utf-8'))
        if args.markdown:
            bundle, provenance = export_markdown(
                args.pdf, args.page, args.markdown, identity,
                args.output.parent / (args.output.stem + '-assets'),
                args.expected_pdf_sha256, args.expected_markdown_sha256, [args.identity, args.output, sidecar],
            )
            provenance['source']['identitySha256'] = hashlib.sha256(identity_bytes).hexdigest()
        else:
            bundle = export_result(args.pdf, args.page, args.result_dir, identity)
        atomic_write(args.output, json_bytes(bundle), inputs)
        if args.markdown:
            atomic_write(sidecar, json_bytes(provenance), inputs)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Export failed: {error}\n')
    print(json.dumps({'output_bytes':args.output.stat().st_size,'pdf_sha256':bundle['pdfSha256'],'covered_pages':[page['page'] for page in bundle['pages']],'blocks':sum(len(page['blocks']) for page in bundle['pages'])}))
