"""Reusable global-device alpha; no local raster or page reader fallback."""
import math
from dataclasses import dataclass,asdict
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_ownership import active
@dataclass(frozen=True)
class DeviceAlphaConfig:
    maximum_reference_pixels:int=32_000_000
    shared_window_policy:str='fixed_initial_padding_plus_one_existing_step'
    outside_ink_policy:str='refuse_without_window_expansion'
    def json(self):return asdict(self)
class DeviceAlphaCanvas:
    def __init__(self,page,scale,cfg=DeviceAlphaConfig()):
        self.page=page;self.cfg=cfg;W,H=page.get_size();self.w=math.ceil(W*scale);self.h=math.ceil(H*scale)
        if self.w*self.h>cfg.maximum_reference_pixels:raise ValueError('global alpha reference exceeds pixel budget')
        self.bitmap=pdfium.PdfBitmap.new_native(self.w,self.h,format=raw.FPDFBitmap_BGRA);self.renders=0;self.calls=[]
    def read(self,handles,pbox,maximum_crop_pixels):
        x0,y0,x1,y1=pbox
        if any(not isinstance(x,int) for x in pbox) or not (0<=x0<x1<=self.w and 0<=y0<y1<=self.h):raise ValueError('invalid fixed device window')
        if (x1-x0)*(y1-y0)>maximum_crop_pixels:raise ValueError('fixed device window exceeds pixel budget')
        raw.FPDFBitmap_FillRect(self.bitmap,0,0,self.w,self.h,0)
        for handle in handles:active(handle,True)
        try:
            raw.FPDF_RenderPageBitmap(self.bitmap,self.page,0,0,self.w,self.h,0,0);self.renders+=1;view=self.bitmap.to_numpy();crop=view[y0:y1,x0:x1];outside=int(np.count_nonzero(view[:,:,3]))-int(np.count_nonzero(crop[:,:,3]));rgba=crop[:,:,[2,1,0,3]].copy()
        finally:
            for handle in handles:active(handle,False)
        self.calls.append({'paint_objects':len(handles),'window_pixels':(x1-x0)*(y1-y0),'global_ink_outside_fixed_window':outside});return rgba,outside
    def close(self):self.bitmap.close()
    def trace(self):return {'config':self.cfg.json(),'allocated_bitmaps':1,'allocated_bgra_bytes':self.w*self.h*4,'native_renders':self.renders,'requests':self.calls,'native_paint_order_preserved':True,'whole_page_reader_image':False}
