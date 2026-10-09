import argparse,json,pathlib,hashlib,sys,types
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
# Register all already-seen alpha paths before executing the primitive comparison.
folders=[root/'generic-reflow-v2-localgeometry-local/control-alpha-v2/native']+[root/f'generic-reflow-v2-integrated-paper-1-local/{n}-cold/native/native' for n in ['H5','H6']]
files=[p for folder in folders for p in sorted(folder.glob('p*-*.png'))];(out/'input-manifest-private.json').write_text(json.dumps([{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2))
import numpy as np
from scipy.ndimage import label as reference_label,find_objects as reference_find
from PIL import Image
from components import label,find_objects
from safe_wire import install
patterns=[np.zeros((0,0),bool),np.zeros((0,5),bool),np.zeros((1,1),bool),np.ones((1,1),bool),np.zeros((7,8),bool),np.ones((7,8),bool),np.eye(7,dtype=bool),np.indices((8,8)).sum(axis=0)%2==0,np.pad(np.ones((3,3),bool),2),np.tri(8,dtype=bool),np.fliplr(np.eye(9,dtype=bool)),np.ones((1,11),bool),np.ones((13,1),bool),np.eye(15,dtype=bool)[::2,::-2]];assert len(patterns)==14
rng=np.random.default_rng(83721);seeded=[rng.random((int(rng.integers(1,80)),int(rng.integers(1,90))))<rng.uniform(.01,.95) for _ in range(400)];cross=np.asarray([[0,1,0],[1,1,1],[0,1,0]],bool);compared=0
for mask in patterns+seeded+[np.array(Image.open(p).convert('RGBA'))[:,:,3]>0 for p in files]:
 for structure in [cross,np.ones((3,3),bool)]:
  old,n=reference_label(mask,structure);new,m=label(mask,structure);assert n==m and np.array_equal(old,new)
  if mask.size:assert reference_find(old)==find_objects(new)
  else:
   for fn,arg in [(reference_find,old),(find_objects,new)]:
    try:fn(arg);raise AssertionError('empty default find_objects did not refuse')
    except ValueError:pass
  compared+=1
refused=0
for array,structure in [(np.zeros((2,2,2)),None),(np.zeros((2,2)),np.ones((5,5))),(np.zeros((2,2)),np.eye(3))]:
 try:label(array,structure);raise AssertionError('unsupported CCL accepted')
 except ValueError:refused+=1
arr,_=label(np.eye(5));
try:find_objects(arr[1:]);raise AssertionError('changed label view accepted')
except ValueError:refused+=1
lazy=types.ModuleType('hostile_lazy_outside_control')
def explode(name):raise AssertionError('outside module lazy attribute was touched')
lazy.__getattr__=explode;sys.modules[lazy.__name__]=lazy
try:install(pathlib.Path(__file__).parent)
finally:sys.modules.pop(lazy.__name__)
result={'authored_patterns':14,'seeded_arrays':400,'existing_alpha_masks':len(files),'connectivities':[4,8],'exact_array_count_and_slices_comparisons':compared,'unsupported_cases_refused':refused,'outside_lazy_module_not_touched':True,'all_passed':True,'new_holdouts_opened':0};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
