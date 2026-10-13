"""Assemble pre-generated Ovis bundles for one local PDF without running a model.

Repeat --input for single-page or multi-page bundles. Pages are sorted, while
block order, recognized text, links and source-PDF crop values stay unchanged.
The adjacent .provenance.json receipt records byte hashes and coverage, without
local filenames. Only the output bundle is needed by Import Ovis result.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import sys
import tempfile

# Share the existing exporter's identity and safe-write primitives. Keep this
# CLI standalone; no model, browser, Node process or new dependency is needed.
_spec = importlib.util.spec_from_file_location(
    '_readest_ovis_export', pathlib.Path(__file__).with_name('export-ovis-result.py'))
_exporter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_exporter)
validate_identity = _exporter.validate_identity
json_bytes = _exporter.json_bytes
check_destination = _exporter.check_destination
atomic_write = _exporter.atomic_write


def require_keys(value, required, optional=(), label='object'):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError(f'Invalid {label}: missing or unknown fields')


def number(value, label, minimum=0, inclusive=False, integer=False):
    try:
        valid = (type(value) in (int, float) and math.isfinite(value)
                 and (value >= minimum if inclusive else value > minimum)
                 and (not integer or value == int(value)))
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'Invalid {label}: expected a finite {"integer" if integer else "number"} in range')


def nonempty(value, label):
    # Match ECMAScript String.trim, including BOM but not Python-only NEL/FS.
    whitespace = ('\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680'
                  '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a'
                  '\u2028\u2029\u202f\u205f\u3000\ufeff')
    if not isinstance(value, str) or not value.strip(whitespace):
        raise ValueError(f'Invalid {label}: expected a nonempty string')


def validate_bundle(bundle):
    """Mirror src/services/academic/ovis.ts parseOvisBundle's strict v1 schema.

    Booleans are not numbers. Optional fields, when present, cannot be null.
    This validates structure, not trusted HTML, OCR correctness or provenance;
    the reader must still sanitize Markdown and render crops from its own PDF.
    """
    require_keys(bundle, ('format', 'version', 'pdfSha256', 'pageCount', 'identity', 'pages'), label='bundle')
    if bundle['format'] != 'readest-ovis-reflow' or type(bundle['version']) not in (int, float) or bundle['version'] != 1:
        raise ValueError('Invalid bundle format or version')
    sha = bundle['pdfSha256']
    if not isinstance(sha, str) or len(sha) != 64 or any(char not in '0123456789abcdef' for char in sha):
        raise ValueError('Invalid PDF SHA-256')
    number(bundle['pageCount'], 'PDF page count', integer=True)
    try:
        validate_identity(bundle['identity'])
    except OverflowError as error:
        raise ValueError('Invalid identity configuration: expected finite values') from error
    if not isinstance(bundle['pages'], list) or not bundle['pages']:
        raise ValueError('Invalid bundle pages: expected a nonempty array')
    pages, ids = set(), set()
    for page in bundle['pages']:
        require_keys(page, ('page', 'width', 'height', 'blocks'), label='page')
        number(page['page'], 'page number', integer=True)
        if page['page'] > bundle['pageCount'] or page['page'] in pages:
            raise ValueError('Duplicate or out-of-range PDF page')
        pages.add(page['page'])
        number(page['width'], 'page width')
        number(page['height'], 'page height')
        if not isinstance(page['blocks'], list) or not page['blocks']:
            raise ValueError('Invalid page blocks: expected a nonempty array')
        for block in page['blocks']:
            if not isinstance(block, dict):
                raise ValueError('Invalid block: expected an object')
            kind = block.get('kind')
            if kind == 'markdown':
                require_keys(block, ('id', 'kind', 'markdown'), label='Markdown block')
                nonempty(block['markdown'], 'Markdown')
            elif kind == 'footnote':
                require_keys(block, ('id', 'kind', 'markdown', 'marker'), label='footnote block')
                nonempty(block['markdown'], 'footnote Markdown')
                nonempty(block['marker'], 'footnote marker')
            elif kind == 'visual':
                require_keys(block, ('id', 'kind', 'role', 'box'), ('caption', 'sourceFontSize'), 'visual block')
                if block['role'] not in ('figure', 'equation'):
                    raise ValueError('Invalid visual role')
                box = block['box']
                require_keys(box, ('x', 'y', 'width', 'height'), label='visual box')
                for key in ('x', 'y', 'width', 'height'):
                    number(box[key], f'visual box {key}', inclusive=key in ('x', 'y'))
                if box['x'] + box['width'] > page['width'] or box['y'] + box['height'] > page['height']:
                    raise ValueError('Visual bounds extend outside the PDF page')
                if 'sourceFontSize' in block:
                    number(block['sourceFontSize'], 'sourceFontSize', minimum=1, inclusive=True)
                if 'caption' in block:
                    nonempty(block['caption'], 'visual caption')
            else:
                raise ValueError('Invalid block kind')
            nonempty(block['id'], 'block ID')
            if block['id'] in ids:
                raise ValueError('Duplicate block IDs')
            ids.add(block['id'])
    return bundle


def load_bundle(raw):
    def reject_constant(value):
        raise ValueError(f'Invalid JSON number: {value}')

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON field: {key}')
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode('utf-8'), parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f'Invalid bundle JSON: {error}') from error
    return validate_bundle(value)


def identities_equal(left, right):
    # Both have already passed validate_identity; configurations are flat.
    # Python otherwise treats True == 1 and False == 0, unlike the app cache.
    if {key: value for key, value in left.items() if key != 'configuration'} != {
            key: value for key, value in right.items() if key != 'configuration'}:
        return False
    a, b = left['configuration'], right['configuration']
    return a.keys() == b.keys() and all(
        a[key] == b[key] and isinstance(a[key], bool) == isinstance(b[key], bool) for key in a)


def merge_results(pdf_path, input_paths, require_complete=False):
    """Validate all sources in memory and return (import bundle, audit receipt)."""
    import fitz
    if not input_paths:
        raise ValueError('At least one input bundle is required')
    pdf_bytes = pdf_path.read_bytes()
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
    pages, ids, inputs, page_sources = {}, set(), [], {}
    identity = None
    with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
        if pdf.needs_pass:
            raise ValueError('The PDF is password protected; open an accessible PDF first')
        page_count = len(pdf)
        for index, path in enumerate(input_paths, 1):
            raw = path.read_bytes()
            input_sha = hashlib.sha256(raw).hexdigest()
            bundle = load_bundle(raw)
            if bundle['pdfSha256'] != pdf_sha:
                raise ValueError(f'Input {index} does not match the supplied PDF SHA-256')
            if bundle['pageCount'] != page_count:
                raise ValueError(f'Input {index} page count does not match the actual PDF')
            if identity is not None and not identities_equal(identity, bundle['identity']):
                raise ValueError(f'Input {index} identity differs from the other inputs')
            identity = bundle['identity'] if identity is None else identity
            for page in bundle['pages']:
                page_number = int(page['page'])
                if page_number in pages:
                    raise ValueError(f'Duplicate PDF page {page_number} across inputs')
                actual = pdf[page_number - 1].rect
                # PyMuPDF uses float32 geometry. This is a numerical tolerance
                # in PDF points, not permission to resize a supplied page/crop.
                if not (math.isclose(page['width'], actual.width, rel_tol=1e-7, abs_tol=1e-4)
                        and math.isclose(page['height'], actual.height, rel_tol=1e-7, abs_tol=1e-4)):
                    raise ValueError(f'Input {index} page {page_number} geometry does not match the actual PDF dimensions')
                for block in page['blocks']:
                    if block['id'] in ids:
                        raise ValueError(f'Duplicate block IDs across inputs: {block["id"]}')
                    ids.add(block['id'])
                pages[page_number] = page
                page_sources[page_number] = {'page': page_number, 'input': index, 'inputSha256': input_sha}
            inputs.append({'input': index, 'sha256': input_sha,
                           'pages': sorted(int(page['page']) for page in bundle['pages'])})
    covered = sorted(pages)
    missing = sorted(set(range(1, page_count + 1)) - pages.keys())
    if require_complete and missing:
        raise ValueError('Missing PDF pages: ' + ', '.join(map(str, missing)))
    merged = {'format': 'readest-ovis-reflow', 'version': 1, 'pdfSha256': pdf_sha,
              'pageCount': page_count, 'identity': identity, 'pages': [pages[number] for number in covered]}
    validate_bundle(merged)
    manifest = {
        'format': 'readest-ovis-merge-provenance', 'version': 1,
        'source': {'pdfSha256': pdf_sha, 'binding': 'producer-declared'},
        'identity': identity, 'bundleSha256': hashlib.sha256(json_bytes(merged)).hexdigest(),
        'adapter': {'version': 'ovis-merge-1', 'pymupdfVersion': fitz.VersionBind},
        'inputs': inputs, 'pages': [page_sources[number] for number in covered],
        'coverage': {'pageCount': page_count, 'coveredPages': covered,
                     'missingPages': missing, 'complete': not missing},
        'verification': {'pdfBytesChecked': True, 'pageGeometryChecked': True,
                         'identityConsistencyChecked': True, 'modelRunAuthenticated': False,
                         'ocrAccuracyChecked': False, 'nativeMathChecked': False},
        'limitations': [
            'Input hashes establish exact bytes, not that a model produced the declared PDF/page output.',
            'Model/runtime/configuration identity is producer-declared; only consistency was checked.',
            'PDF page dimensions were checked, not OCR accuracy, crop semantics or link target existence.',
            'Text, links and source crops are preserved; missing pages and recognition errors are not repaired.',
        ],
    }
    return merged, manifest


def write_outputs(output, bundle, manifest, sources):
    """Stage both files, publish receipt first and commit the bundle last.

    A caught bundle-publication error restores the old receipt. Two separate
    files cannot be crash-atomic; the receipt's bundle hash detects mismatches.
    Only regular, unlinked destinations are replaced; source inputs are safe.
    """
    sidecar = output.with_suffix('.provenance.json')
    if output.name.endswith('.provenance.json') or output.resolve() == sidecar.resolve():
        raise ValueError('Bundle output cannot use the .provenance.json suffix')
    for path in (output, sidecar):
        check_destination(path, sources)
        if path.exists() and not path.is_file():
            raise ValueError('Output destination must be a regular file')
    data, receipt = json_bytes(bundle), json_bytes(manifest)
    staged = []

    def stage(content):
        fd, name = tempfile.mkstemp(dir=output.parent, prefix='.readest-ovis-')
        os.close(fd)
        path = pathlib.Path(name)
        staged.append(path)
        atomic_write(path, content, sources)
        return path

    try:
        bundle_temp, receipt_temp = stage(data), stage(receipt)
        previous = stage(sidecar.read_bytes()) if sidecar.exists() else None
        # Recheck before publishing; os.replace never follows a file symlink.
        for path in (output, sidecar):
            check_destination(path, sources)
        os.replace(receipt_temp, sidecar)
        try:
            os.replace(bundle_temp, output)
        except OSError as error:
            try:
                if previous is None:
                    sidecar.unlink()
                else:
                    os.replace(previous, sidecar)
            except OSError as rollback_error:
                raise OSError('Bundle publication failed and the receipt could not be restored; '
                              'the old bundle remains, but verify the receipt hash before using it') from rollback_error
            raise error
    finally:
        for path in staged:
            path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=pathlib.Path, required=True,
                        help='Original PDF whose bytes and page geometry every input must match')
    parser.add_argument('--input', type=pathlib.Path, action='append', required=True,
                        help='Existing Ovis bundle; repeat once per input (each may contain multiple pages)')
    parser.add_argument('--output', type=pathlib.Path, required=True,
                        help='Merged import JSON; also writes an adjacent .provenance.json receipt')
    parser.add_argument('--require-complete', action='store_true',
                        help='Fail before writing if any page in the actual PDF is missing')
    args = parser.parse_args()
    try:
        bundle, manifest = merge_results(args.pdf, args.input, args.require_complete)
        write_outputs(args.output, bundle, manifest, [args.pdf, *args.input])
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f'Merge failed: {error}\n')
    coverage = manifest['coverage']
    if not coverage['complete']:
        print('Partial Ovis result; missing PDF pages: ' + ', '.join(map(str, coverage['missingPages'])), file=sys.stderr)
    print(json.dumps({'output_bytes': args.output.stat().st_size, 'pdf_sha256': bundle['pdfSha256'],
                      'covered_pages': coverage['coveredPages'], 'missing_pages': coverage['missingPages'],
                      'complete': coverage['complete'], 'blocks': sum(len(page['blocks']) for page in bundle['pages'])}))


if __name__ == '__main__':
    main()
