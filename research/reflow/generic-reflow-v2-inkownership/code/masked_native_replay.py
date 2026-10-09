"""Replay native text actions, then commit only pixels owned by declared units.

The native renderer sees the actual backdrop. Unit masks partition contribution
pixels; independent RGBA snapshots are not used as a replacement compositor.
"""
import argparse,collections,ctypes,hashlib,json,math,pathlib,time
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_ownership import active

def run(pdf,folder,scale=2):
 start=time.perf_counter();folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());records={r['object_id']:r for r in json.loads((folder/'ownership-records.json').read_text())};byobj=collections.defaultdict(list)
 for owner,patches in plan['patches'].items():
  for p in patches:byobj[p['native_object']].append(p)
 doc=pdfium.PdfDocument(pdf);page=doc[0];W,H=page.get_size();width,height=math.ceil(W*scale),math.ceil(H*scale);objects=list(page.get_objects(max_depth=1));states=[]
 refbm=page.render(scale=scale,draw_annots=False,may_draw_forms=False);reference=np.array(refbm.to_pil().convert('RGB'));refbm.close()
 canvas=pdfium.PdfBitmap.new_native(width,height,format=raw.FPDFBitmap_BGR);raw.FPDFBitmap_FillRect(canvas,0,0,width,height,0xffffffff);view=canvas.to_numpy();unowned_changed=0;duplicated=0;quarantine=0
 for obj in objects:
  st=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(obj,st);states.append(bool(st.value));active(obj,False)
 try:
  for i,obj in enumerate(objects):
   oid=f'p{i}';rec=records.get(oid)
   if rec:
    x0,y0,x1,y1=rec['pixel_box'];before=view[y0:y1,x0:x1].copy()
   active(obj,True);raw.FPDF_RenderPageBitmap(canvas,page,0,0,width,height,0,0);active(obj,False)
   if rec:
    after=view[y0:y1,x0:x1].copy();coverage=np.zeros((y1-y0,x1-x0),np.uint16)
    for patch in byobj[oid]:coverage+=(np.array(Image.open(folder/patch['file']))[:,:,3]>0)
    unowned_changed+=int(np.count_nonzero(np.any(before!=after,axis=2)&(coverage==0)));duplicated+=int(np.count_nonzero(coverage>1));quarantine+=rec['quarantined_ink_pixels']
    # Do not keep the unresolved pixels merely because native full replay had them.
    view[y0:y1,x0:x1][coverage==0]=before[coverage==0]
 finally:
  for obj,st in zip(objects,states):active(obj,st)
 actual=np.array(canvas.to_pil().convert('RGB'));canvas.close();diff=np.abs(actual.astype(np.int16)-reference.astype(np.int16));changed=int(np.count_nonzero(np.any(diff,axis=2)))
 result=dict(representation='original-order native paint actions with disjoint per-unit commit masks on the true live backdrop',changed_pixels=changed,max_channel_delta=int(diff.max()),native_text_changed_pixels_without_owner=unowned_changed,duplicated_mask_pixels=duplicated,quarantined_ink_pixels=quarantine,exact_equal=changed==0,ownership_and_replay_pass=changed==0 and unowned_changed==0 and duplicated==0 and quarantine==0,native_renders=1+len(objects),seconds=time.perf_counter()-start,reference_sha256=hashlib.sha256(reference.tobytes()).hexdigest(),replay_sha256=hashlib.sha256(actual.tobytes()).hexdigest(),scope='original position; actual reflow is a separate gate; annotation paint disabled consistently')
 (folder/'masked-native-replay.json').write_text(json.dumps(result,indent=2));Image.fromarray(actual).save(folder/'masked-native-replay.png');page.close();doc.close();return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');a=p.parse_args();print(json.dumps(run(a.pdf,a.folder)))
