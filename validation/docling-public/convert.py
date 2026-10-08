"""Run official Docling standard conversion offline, without custom layout fixes."""
import collections
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import time
import traceback

from PIL import ImageDraw
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode

ROOT = Path('/study')
OUT = Path('/output')
manifest = json.loads((ROOT / 'manifest.json').read_text())
report = {'manifest': manifest, 'pages': [], 'versions': {}, 'network': 'docker --network none',
          'qualityStatus': 'Awaiting independent source and rendered-output comparison'}
for package in ['docling-slim', 'docling-core', 'docling-ibm-models', 'docling-parse', 'torch', 'torchvision']:
    try:
        report['versions'][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        report['versions'][package] = 'not-installed'
artifacts = Path(os.environ['DOCLING_SERVE_ARTIFACTS_PATH'])
assert artifacts.is_dir(), 'Bundled models missing; network download is not permitted'
model_files = []
for path in sorted(artifacts.rglob('*')):
    if path.is_file() and path.suffix in {'.safetensors', '.pt', '.pth', '.onnx'}:
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        model_files.append({'path': str(path.relative_to(artifacts)), 'bytes': path.stat().st_size,
                            'sha256': h.hexdigest()})
report['bundledModels'] = model_files
options = PdfPipelineOptions()
options.artifacts_path = artifacts
options.do_ocr = False
options.do_table_structure = True
options.table_structure_options.mode = TableFormerMode.ACCURATE
options.force_backend_text = False
options.do_code_enrichment = False
options.do_formula_enrichment = False
options.do_picture_classification = False
options.do_picture_description = False
options.enable_remote_services = False
options.allow_external_plugins = False
options.generate_page_images = True
options.generate_picture_images = True
options.images_scale = 2.0
options.document_timeout = 120
options.accelerator_options = AcceleratorOptions(num_threads=2, device=AcceleratorDevice.CPU)
report['pipelineOptions'] = json.loads(options.model_dump_json())
converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})

def save_report():
    report['peakRssMiB'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    (OUT / 'run.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

save_report()
failures = 0
for source in manifest['sources']:
    pdf = ROOT / 'inputs' / (source['key'] + '.pdf')
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == source['sha256']
    for number in source['pages']:
        key = f"{source['key']}-p{number:02d}"
        destination = OUT / key
        destination.mkdir(exist_ok=True)
        entry = {'key': key, 'sourcePage': number}
        report['pages'].append(entry)
        start = time.perf_counter()
        try:
            result = converter.convert(pdf, page_range=(number, number), raises_on_error=True)
            entry['seconds'] = time.perf_counter() - start
            entry['status'] = str(result.status)
            entry['conversionCompleted'] = True
            document = result.document
            document.save_as_json(destination / 'document.json', image_mode=ImageRefMode.PLACEHOLDER)
            document.save_as_markdown(destination / 'document.md', image_mode=ImageRefMode.PLACEHOLDER)
            document.save_as_html(destination / 'reflow.html', image_mode=ImageRefMode.EMBEDDED)
            try:
                document.save_as_html(destination / 'source-and-reflow.html', image_mode=ImageRefMode.EMBEDDED,
                                      split_page_view=True)
            except Exception as export_error:
                entry['optionalSplitViewError'] = type(export_error).__name__ + ': ' + str(export_error)
            items = []
            for item, depth in document.iterate_items():
                items.append({'ref': item.self_ref, 'role': str(item.label), 'depth': depth,
                              'text': getattr(item, 'text', None),
                              'provenance': [p.model_dump(mode='json') for p in item.prov],
                              'captions': [p.model_dump(mode='json') for p in getattr(item, 'captions', [])]})
            (destination / 'ordered-regions.json').write_text(json.dumps(items, indent=2), encoding='utf-8')
            entry['roles'] = dict(collections.Counter(item['role'] for item in items))
            for page_num, page in document.pages.items():
                if page.image is None:
                    raise RuntimeError('Missing source page render')
                image = page.image.pil_image.copy().convert('RGB')
                image.save(destination / 'source.png')
                draw = ImageDraw.Draw(image)
                for index, item in enumerate(items):
                    for prov in item['provenance']:
                        if prov['page_no'] != page_num:
                            continue
                        box = prov['bbox']
                        sx, sy = image.width / page.size.width, image.height / page.size.height
                        left, top, right, bottom = box['l'], box['t'], box['r'], box['b']
                        if str(box.get('coord_origin', '')).upper().endswith('BOTTOMLEFT'):
                            top, bottom = page.size.height - top, page.size.height - bottom
                        coords = (left*sx, min(top,bottom)*sy, right*sx, max(top,bottom)*sy)
                        draw.rectangle(coords, outline='#be123c', width=2)
                        draw.text((coords[0], max(0, coords[1]-12)), f"{index}:{item['role']}", fill='#be123c')
                image.save(destination / 'regions.png')
        except Exception as error:
            entry['seconds'] = time.perf_counter() - start
            entry['error'] = type(error).__name__ + ': ' + str(error)
            (destination / 'error.txt').write_text(traceback.format_exc())
            failures += 1
        save_report()
        print(json.dumps(entry), flush=True)
raise SystemExit(bool(failures))
