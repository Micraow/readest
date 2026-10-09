"""Native action batches on flat backdrops; current-scale ownership is required.

The output contains local word/math/figure assets, never a full-page reader
image. Final native RGB values are retained inside unit support masks; this is
backdrop-dependent paint-action rendering, not generic independent RGBA replay.
"""
import argparse,collections,ctypes,html,json,math,pathlib,statistics,time,unicodedata,sys
PREVIOUS=pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-inkownership/code';sys.path.insert(0,str(PREVIOUS))
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_ownership import active,frozen
from ink_config import UnitRenderConfig

def render_units(pdf,folder,only_kind=None,scale=None,cfg=UnitRenderConfig()):
 padding_pixels=cfg.padding_pixels
 start=time.perf_counter();folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());base=json.loads((folder/'ownership-summary.json').read_text());body=base['body_font'];assets=folder/'units';assets.mkdir(exist_ok=True)
 scale=base['config']['render_scale'] if scale is None else scale
 if scale!=base['config']['render_scale']:raise RuntimeError('ownership masks require rerasterization at the requested sampling grid')
 object_owners=collections.defaultdict(set)
 for uid,ps in plan['patches'].items():
  for patch in ps:object_owners[patch['native_object']].add(uid)
 doc=pdfium.PdfDocument(pdf);page=doc[0];W,H=page.get_size();fullw,fullh=math.ceil(W*scale),math.ceil(H*scale);objects={f'p{i}':o for i,o in enumerate(page.get_objects(max_depth=1))};states={}
 bm=page.render(scale=scale,draw_annots=False,may_draw_forms=False);reference=np.array(bm.to_pil().convert('RGB'));bm.close()
 for oid,obj in objects.items():
  st=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(obj,st);states[oid]=bool(st.value);active(obj,False)
 results=[];renders=1
 try:
  for unit in plan['units']:
   if only_kind and unit['kind']!=only_kind:continue
   b=unit['box'];x0=max(0,math.floor(b[0]*scale)-padding_pixels);y0=max(0,math.floor(b[1]*scale)-padding_pixels);x1=min(fullw,math.ceil(b[2]*scale)+padding_pixels);y1=min(fullh,math.ceil(b[3]*scale)+padding_pixels)
   backgrounds=[bg for bg in plan['backgrounds'] if frozen.inside(bg['box'],b[:2]) and frozen.inside(bg['box'],b[2:])];bg=min(backgrounds,key=lambda bg:frozen.area(bg['box'])) if backgrounds else None;color=bg['rgba'][:3] if bg else list(cfg.paper_background_rgb)
   canvas=pdfium.PdfBitmap.new_native(fullw,fullh,format=raw.FPDFBitmap_BGR);raw.FPDFBitmap_FillRect(canvas,0,0,fullw,fullh,0xff000000|(color[0]<<16)|(color[1]<<8)|color[2]);fullview=canvas.to_numpy();view=fullview[y0:y1,x0:x1];support=np.zeros((y1-y0,x1-x0),bool)
   byobj=collections.defaultdict(list)
   for p in plan['patches'].get(unit['id'],[]):byobj[p['native_object']].append(p)
   paintids=set(unit.get('objects',[]));ids=sorted(set(byobj)|paintids,key=lambda oid:int(oid[1:]))
   # A batch preserves native page paint order inside the same live renderer.
   # Graphic groups may use final native support only when every active text
   # object's visible ownership is inside this group. Otherwise fail closed.
   shared=[oid for oid in ids if object_owners[oid]-{unit['id']}]
   if any(not states[oid] for oid in ids):raise RuntimeError('inactive native paint cannot be promoted into visible unit')
   fallback=bool(paintids and shared)
   if fallback:
    for oid in ids:
     before=view.copy();active(objects[oid],True);raw.FPDF_RenderPageBitmap(canvas,page,0,0,fullw,fullh,0,0);active(objects[oid],False);renders+=1
     if oid in paintids:
      mask=np.any(view!=before,axis=2)
     else:
      mask=np.zeros(support.shape,bool)
      for patch in byobj[oid]:
       px0,py0,px1,py1=patch['pixel_box'];a=np.array(Image.open(folder/patch['file']))[:,:,3]>0;l=max(px0,x0);t=max(py0,y0);r=min(px1,x1);bo=min(py1,y1)
       if l<r and t<bo:mask[t-y0:bo-y0,l-x0:r-x0]|=a[t-py0:bo-py0,l-px0:r-px0]
      view[~mask]=before[~mask]
     support|=mask
   else:
    for oid in ids:active(objects[oid],True)
    try:raw.FPDF_RenderPageBitmap(canvas,page,0,0,fullw,fullh,0,0);renders+=1
    finally:
     for oid in ids:active(objects[oid],False)
    for patches in byobj.values():
     for patch in patches:
      px0,py0,px1,py1=patch['pixel_box'];alpha=np.array(Image.open(folder/patch['file']))[:,:,3]>0;l=max(px0,x0);t=max(py0,y0);r=min(px1,x1);bo=min(py1,y1)
      if l<r and t<bo:support[t-y0:bo-y0,l-x0:r-x0]|=alpha[t-py0:bo-py0,l-px0:r-px0]
    if paintids:support|=np.any(view!=np.asarray(color[::-1],np.uint8),axis=2)
   rgb=view[:,:,::-1].copy();canvas.close()
   if not support.any():
    results.append(dict(id=unit['id'],kind=unit['kind'],empty=True,source_glyph_records=len(unit['glyphs'])));continue
   ys,xs=np.where(support);l,t,r,bo=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1);crop=rgb[t:bo,l:r];mask=support[t:bo,l:r]
   rgba=np.zeros((*crop.shape[:2],4),np.uint8);rgba[:,:,:3]=crop;rgba[:,:,3]=mask*255
   name=unit['id']+'.png';Image.fromarray(rgba,'RGBA').save(assets/name)
   actual=rgb[support];source=reference[y0:y1,x0:x1][support];diff=np.abs(actual.astype(np.int16)-source.astype(np.int16));largest=max((g['size'] for g in unit['glyphs']),default=body);gs=[g for g in unit['glyphs'] if g['size']>=largest*cfg.baseline_major_size_ratio];baseline=unit.get('baseline',statistics.median(g['baseline'] for g in gs) if gs else b[3])
   results.append(dict(id=unit['id'],kind=unit['kind'],file='units/'+name,asset_pixel_box=[x0+l,y0+t,x0+r,y0+bo],width_em=(r-l)/scale/body,height_em=(bo-t)/scale/body,descent_em=((y0+bo)/scale-baseline)/body,source_glyph_records=len(unit['glyphs']),background=color,flat_backdrop_assumption=True,changed_source_support_pixels=int(np.count_nonzero(np.any(diff,axis=1))),max_channel_delta=int(diff.max()) if diff.size else 0,native_paint_actions=len(ids),native_batch_calls=0 if fallback else 1,native_action_fallback_calls=len(ids) if fallback else 0,native_text_objects_shared_with_external_units=shared,source_interval=unit.get('source_interval'),mapped_unicode=''.join(g['char'] for g in unit['glyphs']),all_unicode_known=all(g['unicode_known'] for g in unit['glyphs']),mathematical_selection_verified=False))
 finally:
  for oid,obj in objects.items():active(obj,states[oid])
 result=dict(scope='native action batches, local output only; exact source-support RGB comparison remains mandatory; source flat backdrop only',config=cfg.json(),padding_pixels=padding_pixels,scale=scale,body_font=body,units=len(results),unsupported_source_support_units=[r['id'] for r in results if r.get('changed_source_support_pixels',0)],native_renders=renders,seconds=time.perf_counter()-start,results=results)
 (folder/'native-unit-assets-private.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));page.close();doc.close();return result

def sample_html(folder):
 folder=pathlib.Path(folder);data=json.loads((folder/'native-unit-assets-private.json').read_text());groups=[r for r in data['results'] if r['kind']=='inline_native_group' and not r.get('empty')]
 pieces=[]
 for n,g in enumerate(groups):
  style=f'width:{g["width_em"]}em;height:{g["height_em"]}em;vertical-align:{-g["descent_em"]}em'
  pieces.append(f'<section><p>Before the local expression <img class="group" data-unit="{g["id"]}" style="{style}" src="{g["file"]}" alt="Original local mathematical expression"> after it, the paragraph continues and can wrap at a different width.</p></section>')
 css='''*{box-sizing:border-box}body{margin:0;padding:12px;font:20px/1.5 sans-serif;color:#111}p{margin:0 0 1em}.group{display:inline-block;max-width:none}section{margin:0 0 1em;background:white}'''
 (folder/'shifted-local-group.html').write_text('<!doctype html><html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+''.join(pieces)+'</body></html>')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');p.add_argument('--only-kind');a=p.parse_args();r=render_units(a.pdf,a.folder,a.only_kind);sample_html(a.folder);print(json.dumps({k:v for k,v in r.items() if k!='results'}))
