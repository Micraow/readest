#!/usr/bin/env python3
"""PDFium annotation ink diagnostic. Original code; private inputs stay private.

This is a native-pixel diagnostic, not browser acceptance or general PDF support.
No input is saved or regenerated. Temporary flags and active-state mutations are
restored in finally blocks. Callers must load an independent in-memory document.

Official API references:
https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_annot.h
https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_edit.h
https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_doc.h

One opaque white native base plus independently rendered straight-alpha layers
is only admitted when exact source-over reconstruction equals native pixels.
Non-Normal blends, precision losses, unsupported form widgets, and any other
mismatch fail closed. A match establishes this raster scale only, not arbitrary
backdrops or zoom levels. Original annotation indices define tested paint order.
"""
from __future__ import annotations
import os
import time
_PROCESS_START = time.perf_counter()
_PROCESS_CPU_START = time.process_time()
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import ctypes
import hashlib
import json
import resource
import signal
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def enforce_budget() -> None:
    """CLI one-core / 1 GiB address-space / 60s deadline guard."""
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    signal.alarm(60)


def compare_pixels(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape:
        return {'exact': False, 'shape_mismatch': [list(a.shape), list(b.shape)]}
    delta = np.abs(a.astype(np.int16) - b.astype(np.int16))
    mask = np.any(delta != 0, axis=2)
    yy, xx = np.nonzero(mask)
    return {
        'exact': not bool(mask.any()),
        'changed_pixels': int(mask.sum()),
        'max_channel_delta': int(delta.max(initial=0)),
        'sum_abs_channel_delta': int(delta.sum()),
        'difference_bbox_px': None if len(xx) == 0 else
            [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1],
    }


def alpha_bbox(layer: np.ndarray) -> list[int] | None:
    yy, xx = np.nonzero(layer[:, :, 3])
    return None if not len(xx) else [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def compose_rgba_source_over(base: np.ndarray, layers: list[np.ndarray]) -> np.ndarray:
    """Deterministic Pillow source-over, no tolerance or per-input calibration."""
    image = Image.fromarray(base, 'RGBA')
    for layer in layers:
        if layer.shape != base.shape:
            raise ValueError('All layers must preserve the full native pixel canvas')
        image = Image.alpha_composite(image, Image.fromarray(layer, 'RGBA'))
    return np.asarray(image).copy()


class NativeRenderer:
    """Every actual PDFium render is appended to a durable private JSONL ledger."""
    def __init__(self, page, ledger_path: Path):
        self.page = page
        self.ledger_path = Path(ledger_path)
        self.events: list[dict] = []

    def _write(self, event):
        with self.ledger_path.open('a') as output:
            output.write(json.dumps(event, sort_keys=True) + '\n')

    def render(self, label: str, *, scale=1.0, draw_annots=True, transparent=False):
        event = {'render_id': len(self.events), 'label': label, 'scale': scale,
                 'draw_annots': draw_annots, 'may_draw_forms': False,
                 'fill_rgba': [0, 0, 0, 0] if transparent else [255, 255, 255, 255],
                 'state': 'started'}
        self.events.append(event)
        self._write(event)
        start, cpu = time.perf_counter(), time.process_time()
        bitmap = None
        try:
            bitmap = self.page.render(scale=scale, draw_annots=draw_annots,
                may_draw_forms=False, fill_color=tuple(event['fill_rgba']),
                force_bitmap_format=raw.FPDFBitmap_BGRA, rev_byteorder=True)
            result = np.asarray(bitmap.to_pil()).copy()
            event.update(state='completed', width=int(result.shape[1]),
                         height=int(result.shape[0]), pixels=int(result.shape[0] * result.shape[1]),
                         rgba_sha256=sha256_bytes(result.tobytes()))
            return result
        except Exception as error:
            event.update(state='failed', error_type=type(error).__name__)
            raise
        finally:
            if bitmap is not None:
                bitmap.close()
            event.update(wall_s=time.perf_counter() - start, cpu_s=time.process_time() - cpu)
            self._write(event)


@contextmanager
def annotation_handles(page):
    handles = []
    try:
        for index in range(raw.FPDFPage_GetAnnotCount(page)):
            handle = raw.FPDFPage_GetAnnot(page, index)
            if not handle:
                raise RuntimeError(f'Cannot open annotation {index}')
            handles.append(handle)
        yield handles
    finally:
        for handle in handles:
            raw.FPDFPage_CloseAnnot(handle)


def _native_bytes(getter, *args, max_bytes=1024**2) -> dict:
    """Read a native NUL-terminated byte string; never dereference its target."""
    size = int(getter(*args, None, 0))
    if size <= 0 or size > max_bytes:
        return {'extractable': False, 'native_bytes': size, 'value': None,
                'failure': 'missing_or_api_error' if size <= 0 else 'size_limit'}
    buffer = ctypes.create_string_buffer(size)
    returned = int(getter(*args, buffer, size))
    if returned != size:
        return {'extractable': False, 'native_bytes': size, 'value': None,
                'failure': 'unstable_native_length'}
    value = buffer.raw[:-1] if buffer.raw.endswith(b'\0') else buffer.raw
    try:
        decoded = value.decode('utf-8', errors='strict')
        return {'extractable': True, 'native_bytes': size, 'value': decoded,
                'valid_utf8': True, 'followed_or_opened': False}
    except UnicodeDecodeError:
        return {'extractable': True, 'native_bytes': size, 'value': None,
                'valid_utf8': False, 'private_raw_hex': value.hex(),
                'followed_or_opened': False}


def _native_destination(document, destination) -> dict:
    if not destination:
        return {'present': False, 'extractable': False}
    page_index = int(raw.FPDFDest_GetDestPageIndex(document, destination))
    count = ctypes.c_ulong()
    params = (ctypes.c_float * 4)()
    view_type = int(raw.FPDFDest_GetView(destination, ctypes.byref(count), params))
    has_x, has_y, has_zoom = raw.FPDF_BOOL(), raw.FPDF_BOOL(), raw.FPDF_BOOL()
    x, y, zoom = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
    location_ok = bool(raw.FPDFDest_GetLocationInPage(destination,
        ctypes.byref(has_x), ctypes.byref(has_y), ctypes.byref(has_zoom),
        ctypes.byref(x), ctypes.byref(y), ctypes.byref(zoom)))
    return {'present': True, 'extractable': True, 'page_index': page_index,
            'page_resolved_in_loaded_document': 0 <= page_index < len(document),
            'view_type': view_type, 'view_parameters': list(params)[:min(count.value, 4)],
            'location_xyz_available': location_ok,
            'location_xyz': {'x': x.value if location_ok and has_x.value else None,
                             'y': y.value if location_ok and has_y.value else None,
                             'zoom': zoom.value if location_ok and has_zoom.value else None}}


def extract_link_interaction(page, annotation) -> dict:
    """Private native metadata only; no reflow click mapping or target requests.

    Keep this complete result private: rect/quad coordinates, URI values and
    destination details are native-document data. Use summarize_interactions
    for safe metadata-only reporting. Extractable metadata is NOT functioning
    reflowed link interaction; interaction_supported is deliberately always false.
    """
    result = {'interaction_supported': False,
              'reason': 'reflow_click_region_and_destination_mapping_not_implemented',
              'target_requests': 0, 'native_rect': None, 'quadpoints': [],
              'quadpoints_count': 0, 'quadpoints_complete': False,
              'action_present': False, 'action_type': 'none', 'action_type_code': None,
              'uri': {'extractable': False}, 'file_path': {'extractable': False},
              'link_destination': {'present': False, 'extractable': False},
              'action_destination': {'present': False, 'extractable': False}}
    result['direct_destination_key_present'] = bool(raw.FPDFAnnot_HasKey(annotation, b'Dest'))
    link = raw.FPDFAnnot_GetLink(annotation)
    if not link:
        result['metadata_error'] = 'annotation_has_no_native_link_handle'
        return result
    rect = raw.FS_RECTF()
    if raw.FPDFLink_GetAnnotRect(link, ctypes.byref(rect)):
        result['native_rect'] = [rect.left, rect.bottom, rect.right, rect.top]
    count = raw.FPDFLink_CountQuadPoints(link)
    result['quadpoints_count'] = int(count)
    for index in range(max(0, count)):
        quad = raw.FS_QUADPOINTSF()
        if not raw.FPDFLink_GetQuadPoints(link, index, ctypes.byref(quad)):
            result['metadata_error'] = 'cannot_extract_all_quadpoints'
            break
        result['quadpoints'].append([getattr(quad, field) for field in
                                    ('x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4')])
    result['quadpoints_complete'] = count >= 0 and len(result['quadpoints']) == count
    # Native GetDest may resolve a GoTo action too; do not label it direct /Dest.
    result['link_destination'] = _native_destination(page.pdf, raw.FPDFLink_GetDest(page.pdf, link))
    action = raw.FPDFLink_GetAction(link)
    if action:
        code = int(raw.FPDFAction_GetType(action))
        result.update(action_present=True, action_type_code=code,
            action_type={raw.PDFACTION_UNSUPPORTED: 'unsupported', raw.PDFACTION_GOTO: 'goto',
                raw.PDFACTION_REMOTEGOTO: 'remote_goto', raw.PDFACTION_URI: 'uri',
                raw.PDFACTION_LAUNCH: 'launch', raw.PDFACTION_EMBEDDEDGOTO: 'embedded_goto'}.get(code, 'unknown'))
        if code == raw.PDFACTION_URI:
            result['uri'] = _native_bytes(raw.FPDFAction_GetURIPath, page.pdf, action)
        elif code == raw.PDFACTION_GOTO:
            result['action_destination'] = _native_destination(page.pdf,
                raw.FPDFAction_GetDest(page.pdf, action))
        elif code in (raw.PDFACTION_REMOTEGOTO, raw.PDFACTION_LAUNCH):
            result['file_path'] = _native_bytes(raw.FPDFAction_GetFilePath, action)
            result['remote_destination_resolution'] = 'not_attempted_no_external_document_opened'
    result['native_geometry_extracted'] = result['native_rect'] is not None and result['quadpoints_complete']
    return result


def summarize_interactions(records: list[dict]) -> dict:
    """Allowlisted public summary: no native coordinates, URIs, names or paths."""
    links = [r['interaction'] for r in records if 'interaction' in r]
    return {'link_count': len(links), 'interaction_supported': False,
            'reason': 'reflow_click_region_and_destination_mapping_not_implemented',
            'target_requests': sum(r['target_requests'] for r in links),
            'native_rect_extracted_count': sum(r['native_rect'] is not None for r in links),
            'native_quadpoints_declared': sum(max(0, r['quadpoints_count']) for r in links),
            'quadpoints_complete_count': sum(r['quadpoints_complete'] for r in links),
            'action_types': [r['action_type'] for r in links],
            'uri_extractable_count': sum(r['uri']['extractable'] for r in links),
            'file_path_extractable_count': sum(r['file_path']['extractable'] for r in links),
            'direct_destination_key_present_count': sum(r['direct_destination_key_present'] for r in links),
            'link_destination_present_count': sum(r['link_destination']['present'] for r in links),
            'action_destination_present_count': sum(r['action_destination']['present'] for r in links),
            'internal_destination_page_resolved_count': sum(any(r[k].get('page_resolved_in_loaded_document', False)
                for k in ('link_destination', 'action_destination')) for r in links)}


def annotation_inventory(page, handles) -> list[dict]:
    records = []
    for index, handle in enumerate(handles):
        if raw.FPDFPage_GetAnnotIndex(page, handle) != index:
            raise RuntimeError('Native annotation index mismatch')
        rect = raw.FS_RECTF()
        if not raw.FPDFAnnot_GetRect(handle, ctypes.byref(rect)):
            raise RuntimeError(f'Cannot read annotation rectangle {index}')
        subtype = raw.FPDFAnnot_GetSubtype(handle)
        records.append({
            'index': index, 'native_subtype': subtype,
            'subtype': {raw.FPDF_ANNOT_LINK: 'link', raw.FPDF_ANNOT_STAMP: 'stamp',
                        raw.FPDF_ANNOT_WIDGET: 'widget'}.get(subtype, 'other'),
            'original_flags': raw.FPDFAnnot_GetFlags(handle),
            'rect_pdf': [rect.left, rect.bottom, rect.right, rect.top],
            'normal_ap_utf16_bytes': int(raw.FPDFAnnot_GetAP(handle,
                raw.FPDF_ANNOT_APPEARANCEMODE_NORMAL, None, 0)),
        })
        if subtype == raw.FPDF_ANNOT_LINK:
            records[-1]['interaction'] = extract_link_interaction(page, handle)
    return records


@contextmanager
def keep_annotations(handles, selected: set[int]):
    """Keep original flags on selected annots; hide all others, then restore."""
    originals = [raw.FPDFAnnot_GetFlags(h) for h in handles]
    try:
        for index, (handle, flags) in enumerate(zip(handles, originals)):
            target = flags if index in selected else flags | raw.FPDF_ANNOT_FLAG_HIDDEN
            if not raw.FPDFAnnot_SetFlags(handle, target):
                raise RuntimeError(f'Cannot set annotation flags {index}')
        yield
    finally:
        failed = []
        for index, (handle, flags) in enumerate(zip(handles, originals)):
            if not raw.FPDFAnnot_SetFlags(handle, flags) or raw.FPDFAnnot_GetFlags(handle) != flags:
                failed.append(index)
        if failed:
            raise RuntimeError(f'Failed restoring annotation flags: {failed}')


@contextmanager
def hide_page_content(page):
    """Temporarily hide top-level native content on an in-memory document copy."""
    originals = []
    try:
        for index in range(raw.FPDFPage_CountObjects(page)):
            obj = raw.FPDFPage_GetObject(page, index)
            active = raw.FPDF_BOOL()
            if not raw.FPDFPageObj_GetIsActive(obj, ctypes.byref(active)):
                raise RuntimeError(f'Cannot read active state {index}')
            originals.append((index, obj, active.value))
            if not raw.FPDFPageObj_SetIsActive(obj, False):
                raise RuntimeError(f'Cannot hide native content {index}')
        yield
    finally:
        failed = []
        for index, obj, original in originals:
            check = raw.FPDF_BOOL()
            if (not raw.FPDFPageObj_SetIsActive(obj, original)
                or not raw.FPDFPageObj_GetIsActive(obj, ctypes.byref(check))
                or check.value != original):
                failed.append(index)
        if failed:
            raise RuntimeError(f'Failed restoring active states: {failed}')


def isolate_annotation_appearances(page, renderer: NativeRenderer, scale=1.0,
                                   artifact_dir: Path | None = None) -> dict:
    """Extract per-annot alpha; preserve canvas and native index; exact audit.

    Caller must use an independent in-memory PDF. Returns metadata, including
    native pixels with all annotations vs without, contribution of each isolated
    annotation over the original content, alpha size, exact reconstruction and
    restoration checks. Artifacts are private audit images, never reader output.
    """
    base = renderer.render('base_without_annotations', scale=scale, draw_annots=False)
    source = renderer.render('source_with_annotations', scale=scale)
    result = {'scale': scale, 'source_vs_base': compare_pixels(source, base),
              'composition_operator': 'Pillow straight RGBA source-over in annotation-index order',
              'annotations': [], 'paint_order': [], 'blocking_reasons': []}
    layers = []
    with annotation_handles(page) as handles:
        records = annotation_inventory(page, handles)
        if any(r['native_subtype'] in (raw.FPDF_ANNOT_WIDGET, raw.FPDF_ANNOT_XFAWIDGET) for r in records):
            result['blocking_reasons'].append('widget_form_rendering_not_covered')
        for record in records:
            index = record['index']
            with keep_annotations(handles, {index}):
                solo = renderer.render(f'annotation_{index}_over_content', scale=scale)
                with hide_page_content(page):
                    layer = renderer.render(f'annotation_{index}_alpha', scale=scale, transparent=True)
            reconstruction = compose_rgba_source_over(base, [layer])
            record.update({
                'native_contribution_vs_base': compare_pixels(solo, base),
                'alpha_nonzero_pixels': int(np.count_nonzero(layer[:, :, 3])),
                'alpha_bbox_px': alpha_bbox(layer),
                'alpha_rgba_sha256': sha256_bytes(layer.tobytes()),
                'isolated_reconstruction_vs_native': compare_pixels(reconstruction, solo),
            })
            if not record['isolated_reconstruction_vs_native']['exact']:
                result['blocking_reasons'].append(f'annotation_{index}_backdrop_or_rounding_or_clip_not_exact')
            record['classification'] = (
                'no_ink_in_tested_view' if record['alpha_nonzero_pixels'] == 0 and
                   record['native_contribution_vs_base']['exact'] else
                'visible_appearance_exact_at_tested_view' if
                   record['isolated_reconstruction_vs_native']['exact'] else
                'visible_appearance_rejected_not_exact')
            if artifact_dir is not None:
                Image.fromarray(layer, 'RGBA').save(artifact_dir / f'annotation-{index}-alpha.png')
            layers.append(layer)
            result['annotations'].append(record)
            result['paint_order'].append(index)
        with keep_annotations(handles, set()):
            all_hidden = renderer.render('all_annotations_hidden_control', scale=scale)
        result['all_hidden_vs_draw_annots_false'] = compare_pixels(all_hidden, base)
        if not result['all_hidden_vs_draw_annots_false']['exact']:
            result['blocking_reasons'].append('hidden_flags_do_not_reproduce_no_annots')
        with hide_page_content(page):
            all_alpha = renderer.render('all_annotations_native_alpha', scale=scale, transparent=True)
        empty = np.zeros_like(base)
        independent_alpha = compose_rgba_source_over(empty, layers)
        result['independent_alpha_vs_native_alpha'] = compare_pixels(independent_alpha, all_alpha)
        if not result['independent_alpha_vs_native_alpha']['exact']:
            result['blocking_reasons'].append('annotation_index_order_or_blend_not_exact')
        result['flags_restored'] = all(raw.FPDFAnnot_GetFlags(h) == r['original_flags']
                                      for h, r in zip(handles, records))
    composite = compose_rgba_source_over(base, layers)
    result['reconstruction_vs_source'] = compare_pixels(composite, source)
    if not result['reconstruction_vs_source']['exact']:
        result['blocking_reasons'].append('recomposition_not_exact')
    restored = renderer.render('restored_source', scale=scale)
    result['restored_source_vs_source'] = compare_pixels(restored, source)
    if not result['restored_source_vs_source']['exact'] or not result['flags_restored']:
        result['blocking_reasons'].append('restoration_failed')
    result['interaction'] = summarize_interactions(result['annotations'])
    result['interaction_supported'] = False
    result['annotation_fully_supported'] = False
    result['accepted_at_tested_raster_only'] = not result['blocking_reasons']
    result['no_visible_annotation_ink_at_tested_raster'] = (
        result['source_vs_base']['exact'] and all(
        r['classification'] == 'no_ink_in_tested_view' for r in result['annotations']))
    if artifact_dir is not None:
        for name, pixels in [('source', source), ('base', base), ('recomposed', composite),
                             ('annotations-native-alpha', all_alpha)]:
            Image.fromarray(pixels, 'RGBA').save(artifact_dir / f'{name}.png')
    return result


def _rect_object(rect, rgba, blend='Normal'):
    obj = raw.FPDFPageObj_CreateNewRect(*rect)
    if not obj:
        raise RuntimeError('Cannot create control path')
    if not raw.FPDFPageObj_SetFillColor(obj, *rgba) or not raw.FPDFPath_SetDrawMode(obj, raw.FPDF_FILLMODE_WINDING, False):
        raise RuntimeError('Cannot configure control path')
    raw.FPDFPageObj_SetBlendMode(obj, blend.encode('ascii'))
    return obj


def create_original_control(path: Path, *, alpha=255, blend='Normal') -> dict:
    """Entirely original 200x160 PDF: visible stamp AP + borderless link."""
    doc = pdfium.PdfDocument.new()
    page = doc.new_page(200, 160)
    for rect, color in [((10, 10, 180, 140), (184, 218, 230, 255)),
                        ((20, 60, 160, 20), (44, 92, 130, 255)),
                        ((95, 20, 10, 120), (250, 240, 150, 255))]:
        raw.FPDFPage_InsertObject(page, _rect_object(rect, color))
    if not raw.FPDFPage_GenerateContent(page):
        raise RuntimeError('Cannot generate original control content')
    stamp = raw.FPDFPage_CreateAnnot(page, raw.FPDF_ANNOT_STAMP)
    rect = raw.FS_RECTF(left=40, bottom=50, right=140, top=110)
    if not raw.FPDFAnnot_SetRect(stamp, ctypes.byref(rect)):
        raise RuntimeError('Cannot create original stamp rectangle')
    obj = _rect_object((40, 50, 100, 60), (224, 55, 80, alpha), blend)
    if not raw.FPDFAnnot_AppendObject(stamp, obj):
        raise RuntimeError('Cannot append original stamp appearance')
    raw.FPDFPage_CloseAnnot(stamp)
    link = raw.FPDFPage_CreateAnnot(page, raw.FPDF_ANNOT_LINK)
    rect = raw.FS_RECTF(left=20, bottom=20, right=80, top=35)
    if not raw.FPDFAnnot_SetRect(link, ctypes.byref(rect)) or not raw.FPDFAnnot_SetBorder(link, 0, 0, 0):
        raise RuntimeError('Cannot create original borderless link')
    if not raw.FPDFAnnot_SetURI(link, b'https://example.invalid/original-control'):
        raise RuntimeError('Cannot set original control URI')
    raw.FPDFPage_CloseAnnot(link)
    doc.save(path)
    page.close()
    doc.close()
    return {'file': path.name, 'alpha': alpha, 'blend': blend,
            'sha256': sha256_bytes(path.read_bytes()), 'source': 'entirely_original_native_control'}


def diagnose(source: Path, output_dir: Path, *, key: str, scales=(1.0, 2.0), save_images=False) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(output_dir, 0o700)
    start, cpu = time.perf_counter(), time.process_time()
    data = source.read_bytes()
    before = sha256_bytes(data)
    doc = pdfium.PdfDocument(data)
    page = doc[0]
    result = {'key': key, 'input_sha256_before': before,
              'pdfium_version': str(pdfium.PDFIUM_INFO), 'pypdfium2_version': str(pdfium.PYPDFIUM_INFO),
              'page_index': 0, 'page_size_pdf': list(page.get_size()),
              'form_widget_rendering': 'not_initialized_not_claimed', 'browser_acceptance': False,
              'input_loading': 'read_bytes_to_independent_in_memory_document',
              'input_document_save_calls': 0, 'scales': []}
    renderer = NativeRenderer(page, output_dir / 'render-ledger.jsonl')
    try:
        for scale in scales:
            artifacts = None
            if save_images:
                artifacts = output_dir / f'scale-{scale:g}'
                artifacts.mkdir()
            result['scales'].append(isolate_annotation_appearances(page, renderer, scale, artifacts))
    finally:
        page.close()
        doc.close()
        result['input_sha256_after'] = sha256_bytes(source.read_bytes())
        result['input_bytes_unchanged'] = result['input_sha256_after'] == before
        result['render_count'] = len(renderer.events)
        result['render_pixel_count'] = sum(e.get('pixels', 0) for e in renderer.events)
        result['native_render_and_copy_wall_s'] = sum(e.get('wall_s', 0) for e in renderer.events)
        result['native_render_and_copy_cpu_s'] = sum(e.get('cpu_s', 0) for e in renderer.events)
        result['diagnose_wall_s'] = time.perf_counter() - start
        result['diagnose_cpu_s'] = time.process_time() - cpu
        result['process_to_report_wall_s'] = time.perf_counter() - _PROCESS_START
        result['process_to_report_cpu_s'] = time.process_time() - _PROCESS_CPU_START
        result['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['cpu_affinity'] = list(os.sched_getaffinity(0))
        result['address_space_limit_bytes'] = resource.getrlimit(resource.RLIMIT_AS)[0]
        (output_dir / 'result.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    enforce_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--key', default='original')
    parser.add_argument('--scales', default='1,2')
    parser.add_argument('--save-images', action='store_true')
    parser.add_argument('--create-control', choices=['opaque', 'alpha', 'multiply'])
    args = parser.parse_args()
    if args.create_control:
        params = {'opaque': (255, 'Normal'), 'alpha': (128, 'Normal'), 'multiply': (255, 'Multiply')}[args.create_control]
        print(json.dumps(create_original_control(args.output, alpha=params[0], blend=params[1])))
    else:
        if args.source is None:
            parser.error('--source is required for diagnosis')
        result = diagnose(args.source, args.output, key=args.key,
                          scales=tuple(map(float, args.scales.split(','))), save_images=args.save_images)
        print(json.dumps({'key': result['key'], 'render_count': result['render_count'],
            'input_bytes_unchanged': result['input_bytes_unchanged'],
            'raster_results': [{'scale': r['scale'], 'accepted': r['accepted_at_tested_raster_only'],
                'changed_pixels': r['source_vs_base']['changed_pixels'],
                'recompose_changed_pixels': r['reconstruction_vs_source']['changed_pixels'],
                'blocking_reasons': r['blocking_reasons']} for r in result['scales']]}))


if __name__ == '__main__':
    main()
