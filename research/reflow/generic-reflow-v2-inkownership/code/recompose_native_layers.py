"""Independent original-position, original-paint-order reconstruction check.

Every extracted native text-object partition is recombined before its original
paint event. Other native objects are isolated and replayed in original order.
The strict result is source pixel equality, not a count of conserved alpha.
"""
import argparse,collections,ctypes,hashlib,json,pathlib,time
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_ownership import active,global_pixel_box,isolated_native_layer,stable_native_layer
from ink_config import InkConfig

def check(pdf,folder,config=InkConfig()):
 start=time.perf_counter();folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());records={r['object_id']:r for r in json.loads((folder/'ownership-records.json').read_text())};objpatch=collections.defaultdict(list)
 for owner,patches in plan['patches'].items():
  for patch in patches:objpatch[patch['native_object']].append(patch)
 doc=pdfium.PdfDocument(pdf);page=doc[0];W,H=page.get_size();handles={f'p{i}':o for i,o in enumerate(page.get_objects(max_depth=1))};states={}
 bitmap=page.render(scale=config.render_scale,fill_color=(255,255,255,255),draw_annots=False,may_draw_forms=False);reference=np.asarray(bitmap.to_pil().convert('RGB')).copy();bitmap.close()
 floor_canvas=np.full_like(reference,255);pil_canvas=Image.new('RGBA',(reference.shape[1],reference.shape[0]),'white');extra_renders=1
 for oid,h in handles.items():
  state=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(h,state);states[oid]=bool(state.value);active(h,False)
 layer_records=[]
 try:
  for obj in plan['objects']:
   oid=obj['id']
   if obj['type']==raw.FPDF_PAGEOBJ_TEXT:
    if oid not in records:continue
    rec=records[oid];pbox=rec['pixel_box'];x0,y0,x1,y1=pbox;rgba=np.zeros((y1-y0,x1-x0,4),np.uint8)
    for patch in objpatch[oid]:
     a=np.array(Image.open(folder/patch['file']).convert('RGBA'));mask=a[:,:,3]>0;rgba[mask]=a[mask]
    if rec['quarantined_ink_pixels']:
     a=np.array(Image.open(folder/f'{oid}-UNRESOLVED.png').convert('RGBA'));mask=a[:,:,3]>0;rgba[mask]=a[mask]
   else:
    pbox=global_pixel_box(obj['box'],W,H,config);x0,y0,x1,y1=pbox
    if x1<=x0 or y1<=y0:continue
    rgba,pbox,stability=stable_native_layer(page,handles[oid],obj['box'],config);extra_renders+=stability['native_renders']
   x0,y0,x1,y1=pbox;dst=floor_canvas[y0:y1,x0:x1].astype(np.uint32);src=rgba[:,:,:3].astype(np.uint32);alpha=rgba[:,:,3:4].astype(np.uint32)
   floor_canvas[y0:y1,x0:x1]=((dst*(255-alpha)+src*alpha)//255).astype(np.uint8)
   pil_canvas.alpha_composite(Image.fromarray(rgba,'RGBA'),(x0,y0))
   layer_records.append({'object':oid,'seq':obj['seq'],'pixel_box':pbox,'nonzero_alpha_pixels':int(np.count_nonzero(rgba[:,:,3]))})
 finally:
  for oid,h in handles.items():active(h,states[oid])
 pil_rgb=np.array(pil_canvas.convert('RGB'))
 def metrics(got):
  diff=np.abs(got.astype(np.int16)-reference.astype(np.int16));changed=np.any(diff,axis=2)
  return dict(exact_equal=not bool(changed.any()),changed_pixels=int(changed.sum()),max_channel_delta=int(diff.max()),mean_absolute_channel_delta=float(diff.mean()))
 result=dict(scope='original-position normal source-over replay, original top-level paint order; annotations disabled consistently',primary_compositor='integer floor source-over: (dst*(255-a)+src*a)//255; no fit or tolerance',primary=metrics(floor_canvas),independent_Pillow_source_over=metrics(pil_rgb),native_renders_this_check=extra_renders,layers=len(layer_records),seconds=time.perf_counter()-start,input_sha256=hashlib.sha256(pathlib.Path(pdf).read_bytes()).hexdigest(),source_reference_sha256=hashlib.sha256(reference.tobytes()).hexdigest(),primary_reconstruction_sha256=hashlib.sha256(floor_canvas.tobytes()).hexdigest())
 (folder/'recomposition-result.json').write_text(json.dumps(result,indent=2));(folder/'recomposition-layers.json').write_text(json.dumps(layer_records,indent=2));Image.fromarray(reference).save(folder/'recomposition-reference.png');Image.fromarray(floor_canvas).save(folder/'recomposition-primary.png');Image.fromarray(pil_rgb).save(folder/'recomposition-pillow.png')
 page.close();doc.close();return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');a=p.parse_args();print(json.dumps(check(a.pdf,a.folder)))
