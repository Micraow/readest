"""Load the isolated ownership import variant before any frozen pipeline imports."""
import hashlib,importlib.util,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def identity():
 import cv2
 paths=[HERE/'components.py',HERE/'ink_ownership.py'];return 'opencv-'+cv2.__version__+'-SAUF:'+hashlib.sha256(b''.join(p.read_bytes() for p in paths)).hexdigest()
def load_backend():
 if 'ink_ownership' in sys.modules:raise RuntimeError('ownership backend already loaded; refuse implicit replacement')
 source=(ROOT/'generic-reflow-v2-inkownership/code/ink_ownership.py').read_text();variant=(HERE/'ink_ownership.py').read_text()
 if source.replace('from scipy.ndimage import label,find_objects','from components import label,find_objects')!=variant:raise RuntimeError('unexpected ownership source change')
 sys.path.insert(0,str(ROOT/'generic-reflow-v2-inkownership/code'));spec=importlib.util.spec_from_file_location('ink_ownership',HERE/'ink_ownership.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return {'backend':identity(),'only_ownership_change':'component imports','source_sha256':hashlib.sha256(source.encode()).hexdigest(),'variant_sha256':hashlib.sha256(variant.encode()).hexdigest(),'new_downloads':0}
def bind_asset_identity():
 import asset_service,render_request
 old=asset_service.renderer_identity;tag=identity()
 def combined(version):return old(version)+';component-backend:'+tag
 asset_service.renderer_identity=combined;render_request.renderer_identity=combined
