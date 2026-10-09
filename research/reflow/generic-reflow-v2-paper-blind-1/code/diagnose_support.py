"""Post-blind read-only diagnostic: locate changed pixels and missing live support."""
import argparse,collections,ctypes,json,math,pathlib,sys,time
import numpy as np
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from scipy.ndimage import label,find_objects
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('plan');p.add_argument('out');a=p.parse_args();folder=pathlib.Path(a.plan);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
plan=json.loads((folder/'plan-private.json').read_text());records={r['object_id']:r for r in json.loads((folder/'ownership-records.json').read_text())};byobj=collections.defaultdict(list)
for owner,ps in plan['patches'].items():
 for patch in ps:byobj[patch['native_object']].append((owner,patch))
doc=pdfium.PdfDocument(a.pdf);page=doc[0];W,H=page.get_size();w,h=math.ceil(W*2),math.ceil(H*2);objects=list(page.get_objects(max_depth=1));states=[]
def active(o,v):
 if not raw.FPDFPageObj_SetIsActive(o,v):raise RuntimeError('activation failure')
bm=page.render(scale=2,draw_annots=False,may_draw_forms=False);ref=np.array(bm.to_pil().convert('RGB'));bm.close();Image.fromarray(ref).save(out/'source-reference.png')
canvas=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGR);raw.FPDFBitmap_FillRect(canvas,0,0,w,h,0xffffffff);view=canvas.to_numpy();rows=[]
for o in objects:
 st=ctypes.c_int();raw.FPDFPageObj_GetIsActive(o,st);states.append(bool(st.value));active(o,False)
try:
 for i,o in enumerate(objects):
  oid=f'p{i}';rec=records.get(oid)
  if rec:
   x0,y0,x1,y1=rec['pixel_box'];before=view[y0:y1,x0:x1].copy()
  active(o,True);raw.FPDF_RenderPageBitmap(canvas,page,0,0,w,h,0,0);active(o,False)
  if rec:
   after=view[y0:y1,x0:x1].copy();coverage=np.zeros((y1-y0,x1-x0),np.uint16)
   for owner,patch in byobj[oid]:coverage+=np.array(Image.open(folder/patch['file']))[:,:,3]>0
   missed=np.any(before!=after,axis=2)&(coverage==0)
   if missed.any():
    yy,xx=np.where(missed);row={'object':oid,'count':len(xx),'box_pixels':[int(xx.min())+x0,int(yy.min())+y0,int(xx.max())+x0+1,int(yy.max())+y0+1],'max_channel_delta':int(np.abs(before.astype(np.int16)-after.astype(np.int16))[missed].max()),'points':[{'x':int(x)+x0,'y':int(y)+y0,'before_rgb':before[y,x,::-1].tolist(),'after_rgb':after[y,x,::-1].tolist()} for y,x in zip(yy,xx)]};rows.append(row)
   view[y0:y1,x0:x1][coverage==0]=before[coverage==0]
finally:
 for o,st in zip(objects,states):active(o,st)
actual=np.array(canvas.to_pil().convert('RGB'));canvas.close();diff=np.any(actual!=ref,axis=2);labs,_=label(diff,np.ones((3,3)));components=[]
for n,sl in enumerate(find_objects(labs),1):
 if sl is None:continue
 y,x=sl;box=[x.start,y.start,x.stop,y.stop];pad=16;crop=[max(0,x.start-pad),max(0,y.start-pad),min(w,x.stop+pad),min(h,y.stop+pad)];im=Image.fromarray(ref).crop(crop);im.save(out/f'difference-{n:02d}-source.png');components.append({'component':n,'box_pixels':box,'count':int(np.count_nonzero(labs[sl]==n))})
angles=[];tp=page.get_textpage()
for i in range(tp.count_chars()):
 angle=float(raw.FPDFText_GetCharAngle(tp,i))
 if abs(angle)>1e-5:angles.append({'source_index':i,'angle_radians':angle})
result={'scope':'post-blind diagnostics; no ownership repaired or source evidence overwritten','changed_pixels':int(diff.sum()),'objects_with_live_ink_without_transparent_alpha_owner':rows,'components':components,'rotated_glyphs':angles};(out/'support-diagnostic-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({'missing_objects':len(rows),'changed_pixels':int(diff.sum()),'components':len(components),'rotated_glyphs':len(angles)}));tp.close();page.close();doc.close()
