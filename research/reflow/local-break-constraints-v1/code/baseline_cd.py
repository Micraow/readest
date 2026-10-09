"""Frozen C/D at390px reader defaults; bounded ephemeral PPM intermediates."""
import pathlib,sys,json,tempfile,importlib.util
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent;key=sys.argv[1];O=B/'output'/(key+'-CD')
for n in ['inputs','output','evidence']: (O/n).mkdir(parents=True,exist_ok=True)
for dest,src in [(O/'inputs'/(key+'.pdf'),B/'inputs'/(key+'.pdf')),(O/'output'/(key+'-detector.json'),B/'output'/(key+'-detector.json'))]:
 if not dest.exists():dest.symlink_to(src.resolve())
sys.path.insert(0,str(W/'stroke-object-batch-v1/code'));import compose,helpers
spec=importlib.util.spec_from_file_location('stencil_envelope',W/'stencil-paint-v1/code/envelope.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);compose.inspect=m.inspect;compose.B=O;helpers.B=O;original=helpers.k2
# Output PNGs and map JSON preserve evidence; PPM scratch files are reproducible.
def compact_k2(im,name):
 try:return original(im,name)
 finally:
  for suffix in ['-input.ppm','.ppm']:
   f=O/'output'/(name+suffix)
   if f.exists():f.unlink()
compose.k2=compact_k2;compose.main({'key':key,'page_1based':1})
