"""Full-device native alpha: crop arrays, never rerasterize a floating PDF crop."""
import ctypes,math,pathlib,sys
from dataclasses import dataclass,asdict
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-inkownership/code'))
import ink_ownership as ink
@dataclass(frozen=True)
class GlobalAlphaConfig:
    maximum_reference_pixels:int=4_000_000
    array_crop_padding_pixels:int=2
    def json(self):return asdict(self)
def global_layer(page,handle,box,config,cfg=GlobalAlphaConfig()):
    W,H=page.get_size();w,h=math.ceil(W*config.render_scale),math.ceil(H*config.render_scale)
    if w*h>cfg.maximum_reference_pixels:raise RuntimeError('full native alpha reference exceeds declared pixel bound')
    bitmap=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGRA);raw.FPDFBitmap_FillRect(bitmap,0,0,w,h,0);ink.active(handle,True)
    try:
        raw.FPDF_RenderPageBitmap(bitmap,page,0,0,w,h,0,0);view=bitmap.to_numpy();ys,xs=np.where(view[:,:,3]>0)
        if len(xs):
            p=cfg.array_crop_padding_pixels;pbox=[max(0,int(xs.min())-p),max(0,int(ys.min())-p),min(w,int(xs.max())+p+1),min(h,int(ys.max())+p+1)]
        else:pbox=ink.global_pixel_box(box,W,H,config)
        x0,y0,x1,y1=pbox;rgba=view[y0:y1,x0:x1][:,:,[2,1,0,3]].copy()
        outside=len(xs)-int(np.count_nonzero(rgba[:,:,3]));assert outside==0
    finally:ink.active(handle,False);bitmap.close()
    return rgba,pbox,dict(stable=True,native_renders=1,attempts=[],mask_source='full_integer_device_canvas_alpha_then_array_crop',full_global_ink_outside_crop=outside,config=cfg.json())
def extract(pdf,out,config=ink.InkConfig(),page_index=0,experimental_fraction_support=False):
    from direction_groups import group
    import json
    previous=ink.stable_native_layer;previous_inventory=ink.frozen.native_inventory;previous_units=ink.ownership_units;previous_plan=ink.frozen.plan;context={}
    def inventory(page,cfg,trace):
        result=previous_inventory(page,cfg,trace);tp=page.get_textpage()
        try:
            for g in result[2]:g['native_angle_radians']=float(raw.FPDFText_GetCharAngle(tp,g['source_index']))
        finally:tp.close()
        context.update(page_size=list(page.get_size()),glyphs=result[2]);return result
    def plan(*args,**kwargs):
        from fraction_support import propose_support
        if experimental_fraction_support:kwargs['fraction_support_selector']=propose_support
        return previous_plan(*args,**kwargs)
    def units(items):
        us,owners=previous_units(items)
        grouped,trace=group({'units':us,'glyphs':context['glyphs'],'page_size':context['page_size'],'patches':{}})
        context['direction_trace']=trace
        if any(not t['accepted'] and t.get('changes_required',True) for t in trace):raise RuntimeError('mixed/nonclosed native direction cannot be safely partitioned')
        us=grouped['units'];return us,{g['id']:u['id'] for u in us for g in u['glyphs']}
    ink.stable_native_layer=global_layer;ink.frozen.native_inventory=inventory;ink.ownership_units=units;ink.frozen.plan=plan
    try:
        result=ink.extract_partitioned_layers(pdf,out,config,page_index);(pathlib.Path(out)/'direction-trace-private.json').write_text(json.dumps(context.get('direction_trace',[]),indent=2));return result
    finally:ink.stable_native_layer=previous;ink.frozen.native_inventory=previous_inventory;ink.ownership_units=previous_units;ink.frozen.plan=previous_plan
