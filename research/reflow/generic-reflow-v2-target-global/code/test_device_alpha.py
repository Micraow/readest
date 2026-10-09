import argparse,ctypes,json,pathlib,sys
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-native-components/code'))
from backend_loader import load_backend
load_backend();sys.path.insert(0,str(ROOT/'generic-reflow-v2-targetgrid/code'))
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from device_alpha import DeviceAlphaCanvas,DeviceAlphaConfig
from ink_config import InkConfig
from ink_ownership import active
from native_target_layer import full_object_reference,full_text_set_reference
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);doc=pdfium.PdfDocument(a.pdf);page=doc[0];handles=list(page.get_objects(max_depth=1));states=[]
for h in handles:
 s=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(h,s);states.append(bool(s.value));active(h,False)
canvas=DeviceAlphaCanvas(page,2);pbox=[0,0,canvas.w,canvas.h];comparisons=0;negative=0
try:
 for h in handles:
  x,n=canvas.read([h],pbox,canvas.w*canvas.h);y,m=full_object_reference(page,h,pbox,InkConfig(render_scale=2));assert n==m==0 and np.array_equal(x,y);comparisons+=1
 selected=[h for h,state in zip(handles,states) if state];x,n=canvas.read(selected,pbox,canvas.w*canvas.h);y,m=full_text_set_reference(page,selected,pbox,InkConfig(render_scale=2));assert n==m==0 and np.array_equal(x,y);comparisons+=1
 x,n=canvas.read(selected,[0,0,1,1],1);assert n>0;negative+=1
 for f in [lambda:DeviceAlphaCanvas(page,2,DeviceAlphaConfig(maximum_reference_pixels=1)),lambda:canvas.read(selected,pbox,1),lambda:canvas.read(selected,[-1,0,1,1],4)]:
  try:f()
  except ValueError:negative+=1
  else:raise AssertionError('negative control did not refuse')
 report={'independent_full_RGBA_exact_cases':comparisons,'negative_controls':negative,'all_passed':True,'canvas':canvas.trace()};(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
 canvas.close()
 for h,s in zip(handles,states):active(h,s)
 page.close();doc.close()
