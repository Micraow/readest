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
import sys

from PIL import ImageDraw
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.datamodel.vlm_engine_options import TransformersVlmEngineOptions
from docling.datamodel.pipeline_options import VlmPipelineOptions, VlmConvertOptions
from docling.pipeline.vlm_pipeline import VlmPipeline
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
artifacts = Path('/study/models')
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
vlm=VlmConvertOptions.from_preset('granite_docling', engine_options=TransformersVlmEngineOptions(
    device=AcceleratorDevice.CPU, compile_model=False, torch_dtype='float32',
    load_in_8bit=False, trust_remote_code=False))
vlm.model_spec=vlm.model_spec.model_copy(deep=True)
vlm.model_spec.revision=manifest['model']['revision']
assert vlm.model_spec.prompt=='Convert this page to docling.'
assert vlm.model_spec.max_new_tokens==8192
vlm.force_backend_text=False
vlm.batch_size=1
options=VlmPipelineOptions(vlm_options=vlm)
options.artifacts_path=artifacts
options.enable_remote_services=False
options.allow_external_plugins=False
options.generate_page_images=True
options.generate_picture_images=True
options.images_scale=2.0
options.document_timeout=295
options.accelerator_options=AcceleratorOptions(num_threads=2,device=AcceleratorDevice.CPU)
report['vlmOptions']=json.loads(vlm.model_dump_json())
report['pipelineOptions'] = json.loads(options.model_dump_json())
converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline,pipeline_options=options)})

def save_report():
    report['peakRssMiB'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    (OUT / f'run-{sys.argv[1]}-p{int(sys.argv[2]):02d}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

save_report()
failures = 0
for source in manifest['sources']:
    if source['key'] != sys.argv[1]:
        continue
    pdf = ROOT / 'inputs' / (source['key'] + '.pdf')
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == source['sha256']
    for number in source['pages']:
        if number != int(sys.argv[2]):
            continue
        key = f"{source['key']}-p{number:02d}"
        destination = OUT / key
        destination.mkdir(exist_ok=True)
        entry = {'key': key, 'sourcePage': number}
        report['pages'].append(entry)
        start = time.perf_counter()
        try:
            result = converter.convert(pdf, page_range=(number, number), raises_on_error=False)
            entry['seconds'] = time.perf_counter() - start
            entry['status'] = str(result.status)
            entry['errors'] = [error.model_dump(mode='json') for error in result.errors]
            entry['vlmPredictions']=[]
            for converted_page in result.pages:
                prediction=converted_page.predictions.vlm_response
                if prediction is not None:
                    raw=prediction.model_dump(mode='json')
                    (destination/'raw-prediction.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2))
                    (destination/'raw.doctags').write_text(prediction.text,encoding='utf-8')
                    entry['vlmPredictions'].append({k:raw.get(k) for k in ['num_tokens','generation_time','stop_reason']})
                    if raw.get('stop_reason') not in ['end_of_sequence','stop_sequence']:
                        raise RuntimeError('Incomplete or unknown VLM stop reason: '+str(raw.get('stop_reason')))
                    if raw.get('num_tokens') is not None and raw['num_tokens'] >= 8192:
                        raise RuntimeError('VLM reached output token limit')
            if not entry['vlmPredictions']:
                raise RuntimeError('No raw VLM prediction retained')
            if result.status != ConversionStatus.SUCCESS or entry['errors']:
                raise RuntimeError('Conversion status or errors failed: ' + json.dumps(entry))
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
if len(report['pages']) != 1 or any(not page.get('conversionCompleted') or page.get('error')
                                  or page.get('errors') for page in report['pages']):
    failures += 1
report['pageConvertedAndExported'] = failures == 0
save_report()
raise SystemExit(bool(failures))
