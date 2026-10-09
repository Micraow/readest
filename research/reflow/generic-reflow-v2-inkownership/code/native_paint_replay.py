"""Original-order replay with the native renderer drawing onto the live backdrop.

This is deliberately a different representation from independent 8-bit alpha
layers: the retained object is a native paint action. It is an original-position
audit, not a full-page-image reading result or proof of reflow semantics.
"""
import argparse,ctypes,hashlib,json,math,pathlib,time
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from PIL import Image
from ink_ownership import active

def run(pdf,output,scale=2):
 started=time.perf_counter();out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
 doc=pdfium.PdfDocument(pdf);page=doc[0];W,H=page.get_size();width,height=math.ceil(W*scale),math.ceil(H*scale);objects=list(page.get_objects(max_depth=1));states=[]
 b=page.render(scale=scale,fill_color=(255,255,255,255),draw_annots=False,may_draw_forms=False);ref=np.array(b.to_pil().convert('RGB'));b.close()
 # BGR format matches the reference. The renderer paints on the existing buffer;
 # it is not cleared between retained native-object actions.
 canvas=pdfium.PdfBitmap.new_native(width,height,format=raw.FPDFBitmap_BGR)
 raw.FPDFBitmap_FillRect(canvas,0,0,width,height,0xffffffff)
 for obj in objects:
  state=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(obj,state);states.append(bool(state.value));active(obj,False)
 try:
  for obj in objects:
   active(obj,True)
   raw.FPDF_RenderPageBitmap(canvas,page,0,0,width,height,0,0)
   active(obj,False)
 finally:
  for obj,state in zip(objects,states):active(obj,state)
 actual=np.array(canvas.to_pil().convert('RGB'));canvas.close();diff=np.abs(actual.astype(np.int16)-ref.astype(np.int16))
 result=dict(representation='native object actions on the actual accumulated backdrop, not separately quantized RGBA source-over',scale=scale,native_renders=1+len(objects),source_paint_objects=len(objects),changed_pixels=int(np.count_nonzero(np.any(diff,axis=2))),max_channel_delta=int(diff.max()),exact_equal=bool(np.array_equal(actual,ref)),seconds=time.perf_counter()-started,reference_sha256=hashlib.sha256(ref.tobytes()).hexdigest(),replay_sha256=hashlib.sha256(actual.tobytes()).hexdigest(),annotations='consistently disabled for this paint-content test',reflow_semantics='not tested')
 (out/'native-paint-replay.json').write_text(json.dumps(result,indent=2));Image.fromarray(actual).save(out/'native-paint-replay.png');page.close();doc.close();return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('output');a=p.parse_args();print(json.dumps(run(a.pdf,a.output)))
