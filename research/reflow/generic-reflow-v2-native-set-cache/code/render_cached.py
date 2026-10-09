"""Reuse native_word text paint sets; preserve all original support checks."""
import argparse,collections,ctypes,importlib.util,json,math,pathlib,statistics,sys,time
from dataclasses import dataclass,asdict
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as raw
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-localcanvas/code'))
from render_native_localcanvas import render_units as original
from ink_ownership import active,frozen
@dataclass(frozen=True)
class SetCacheConfig:
    maximum_cached_rgb_bytes:int=32*1024*1024
    supported_unit_kind:str='native_word'
    padding_pixels:int=8
    baseline_major_size_ratio:float=.86
    paper_background_rgb:tuple[int,int,int]=(255,255,255)
    def json(self):return asdict(self)
def render_units(pdf,folder,only_kind=None,scale=None,cfg=SetCacheConfig()):
    start=time.perf_counter();folder=pathlib.Path(folder);plan=json.loads((folder/'plan-private.json').read_text());base=json.loads((folder/'ownership-summary.json').read_text());scale=base['config']['render_scale'] if scale is None else scale;body=base['body_font'];W,H=plan['page_size'];w,h=math.ceil(W*scale),math.ceil(H*scale);eligible=[u for u in plan['units'] if u['kind']==cfg.supported_unit_kind]
    if scale!=base['config']['render_scale']:raise ValueError('fresh masks required at this scale')
    if only_kind or w*h*3>cfg.maximum_cached_rgb_bytes or any(u.get('objects') for u in eligible):return original(pdf,folder,only_kind,scale)
    # Delegate whole nonword kinds unchanged, including graphics and rotation.
    delegated=[];results=[];renders=0
    for kind in sorted({u['kind'] for u in plan['units'] if u['kind']!=cfg.supported_unit_kind}):
        r=original(pdf,folder,only_kind=kind,scale=scale);delegated.append({'kind':kind,'renders':r['native_renders']});results.extend(r['results']);renders+=r['native_renders']
    assets=folder/'units';assets.mkdir(exist_ok=True);owners=collections.defaultdict(set)
    for uid,ps in plan['patches'].items():
        for patch in ps:owners[patch['native_object']].add(uid)
    doc=pdfium.PdfDocument(pdf);page=doc[base['page_index']];bitmap=page.render(scale=scale,draw_annots=False,may_draw_forms=False);reference=np.array(bitmap.to_pil().convert('RGB'));bitmap.close();renders+=1;handles={f'p{i}':v for i,v in enumerate(page.get_objects(max_depth=1))};states={}
    for oid,obj in handles.items():
        state=ctypes.c_int();assert raw.FPDFPageObj_GetIsActive(obj,state);states[oid]=bool(state.value);active(obj,False)
    cache=collections.OrderedDict();cached=0;peak=0;hits=0;misses=0;evictions=0;canvas=None
    try:
        for unit in eligible:
            b=unit['box'];pad=cfg.padding_pixels;x0=max(0,math.floor(b[0]*scale)-pad);y0=max(0,math.floor(b[1]*scale)-pad);x1=min(w,math.ceil(b[2]*scale)+pad);y1=min(h,math.ceil(b[3]*scale)+pad);patches=plan['patches'].get(unit['id'],[]);ids=tuple(sorted({p['native_object'] for p in patches},key=lambda x:int(x[1:])))
            if any(not states[oid] for oid in ids):raise ValueError('inactive source object cannot be promoted')
            backgrounds=[bg for bg in plan['backgrounds'] if frozen.inside(bg['box'],b[:2]) and frozen.inside(bg['box'],b[2:])];bg=min(backgrounds,key=lambda x:frozen.area(x['box'])) if backgrounds else None;color=tuple(bg['rgba'][:3] if bg else cfg.paper_background_rgb);key=(ids,color);hit=key in cache
            if hit:frame=cache.pop(key);cache[key]=frame;hits+=1
            else:
                while cache and cached+w*h*3>cfg.maximum_cached_rgb_bytes:
                    _,old=cache.popitem(last=False);cached-=old.nbytes;evictions+=1
                if canvas is None:canvas=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGR)
                raw.FPDFBitmap_FillRect(canvas,0,0,w,h,0xff000000|(color[0]<<16)|(color[1]<<8)|color[2])
                for oid in ids:active(handles[oid],True)
                try:raw.FPDF_RenderPageBitmap(canvas,page,0,0,w,h,0,0);frame=canvas.to_numpy().copy();renders+=1
                finally:
                    for oid in ids:active(handles[oid],False)
                frame.setflags(write=False);cache[key]=frame;cached+=frame.nbytes;peak=max(peak,cached);misses+=1
            support=np.zeros((y1-y0,x1-x0),bool)
            for patch in patches:
                px0,py0,px1,py1=patch['pixel_box'];alpha=np.array(Image.open(folder/patch['file']))[:,:,3]>0;l=max(px0,x0);t=max(py0,y0);r=min(px1,x1);bo=min(py1,y1)
                if l<r and t<bo:support[t-y0:bo-y0,l-x0:r-x0]|=alpha[t-py0:bo-py0,l-px0:r-px0]
            if not support.any():results.append({'id':unit['id'],'kind':unit['kind'],'empty':True,'source_glyph_records':len(unit['glyphs'])});continue
            rgb=frame[y0:y1,x0:x1,::-1].copy();diff=np.abs(rgb[support].astype(np.int16)-reference[y0:y1,x0:x1][support].astype(np.int16));changed=int(np.count_nonzero(np.any(diff,axis=1)));ys,xs=np.where(support);l,t,r,bo=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1);rgba=np.zeros((bo-t,r-l,4),np.uint8);rgba[:,:,:3]=rgb[t:bo,l:r];rgba[:,:,3]=support[t:bo,l:r]*255;name=unit['id']+'.png';Image.fromarray(rgba,'RGBA').save(assets/name);largest=max((g['size'] for g in unit['glyphs']),default=body);gs=[g for g in unit['glyphs'] if g['size']>=largest*cfg.baseline_major_size_ratio];baseline=unit.get('baseline',statistics.median(g['baseline'] for g in gs) if gs else b[3]);results.append({'id':unit['id'],'kind':unit['kind'],'file':'units/'+name,'asset_pixel_box':[x0+l,y0+t,x0+r,y0+bo],'width_em':(r-l)/scale/body,'height_em':(bo-t)/scale/body,'descent_em':((y0+bo)/scale-baseline)/body,'source_glyph_records':len(unit['glyphs']),'background':list(color),'flat_backdrop_assumption':True,'local_canvas_used':False,'native_set_cache_hit':hit,'changed_source_support_pixels':changed,'max_channel_delta':int(diff.max()) if diff.size else 0,'native_paint_actions':len(ids),'native_batch_calls':0 if hit else 1,'native_action_fallback_calls':0,'native_text_objects_shared_with_external_units':[oid for oid in ids if owners[oid]-{unit['id']}],'source_interval':unit.get('source_interval'),'mapped_unicode':''.join(g['char'] for g in unit['glyphs']),'all_unicode_known':all(g['unicode_known'] for g in unit['glyphs']),'mathematical_selection_verified':False})
    finally:
        if canvas is not None:canvas.close()
        for oid,obj in handles.items():active(obj,states[oid])
        page.close();doc.close()
    byid={u['id']:i for i,u in enumerate(plan['units'])};results.sort(key=lambda a:byid[a['id']]);result={'scope':'bounded cache of identical native text paint sets; per-unit exact native source RGB gate retained','config':cfg.json(),'scale':scale,'body_font':body,'units':len(results),'unsupported_source_support_units':[r['id'] for r in results if r.get('changed_source_support_pixels',0)],'native_renders':renders,'seconds':time.perf_counter()-start,'set_cache':{'hits':hits,'misses':misses,'evictions':evictions,'peak_rgb_bytes':peak,'maximum_rgb_bytes':cfg.maximum_cached_rgb_bytes,'delegated_nonword_kinds':delegated},'results':results};(folder/'native-unit-assets-private.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');a=p.parse_args();r=render_units(a.pdf,a.folder);print(json.dumps({k:v for k,v in r.items() if k!='results'}))
