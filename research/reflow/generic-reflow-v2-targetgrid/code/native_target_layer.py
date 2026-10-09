"""Integer device-coordinate alpha viewport; avoid float crop-to-pixel rounding."""
import math
from dataclasses import replace
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from ink_ownership import active,global_pixel_box

def layer(page,handle,pbox,config):
    W,H=page.get_size();s=config.render_scale;x0,y0,x1,y1=pbox;w,h=x1-x0,y1-y0
    if w*h>config.maximum_bitmap_pixels:raise RuntimeError('target native object exceeds pixel budget')
    bitmap=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGRA);raw.FPDFBitmap_FillRect(bitmap,0,0,w,h,0)
    active(handle,True)
    try:raw.FPDF_RenderPageBitmap(bitmap,page,-x0,-y0,math.ceil(W*s),math.ceil(H*s),0,0);rgba=np.array(bitmap.to_pil().convert('RGBA'))
    finally:active(handle,False);bitmap.close()
    return rgba

def stable_target_layer(page,handle,box,config):
    W,H=page.get_size();previous=None;attempts=[];calls=0
    for padding in range(config.crop_padding_pixels,config.crop_padding_limit_pixels+1,config.crop_padding_step_pixels):
        cfg=replace(config,crop_padding_pixels=padding);pbox=global_pixel_box(box,W,H,cfg);rgba=layer(page,handle,pbox,cfg);calls+=1
        if previous is not None:
            old,oldbox=previous;l,t=oldbox[0]-pbox[0],oldbox[1]-pbox[1];h,w=old.shape[:2];inside=np.zeros(rgba.shape[:2],bool);inside[t:t+h,l:l+w]=True;outside=int(np.count_nonzero((rgba[:,:,3]>0)&~inside));same=np.array_equal(rgba[t:t+h,l:l+w],old);attempts.append(dict(padding_pixels=padding,common_rgba_equal=same,outside_prior_viewport_ink_pixels=outside))
            if same and outside==0:return rgba,pbox,dict(stable=True,native_renders=calls,attempts=attempts)
        previous=(rgba,pbox)
    return rgba,pbox,dict(stable=False,native_renders=calls,attempts=attempts)

def full_object_reference(page,handle,pbox,config):
    """Independent complete-object alpha baseline; never a reader image."""
    W,H=page.get_size();s=config.render_scale;w,h=math.ceil(W*s),math.ceil(H*s);x0,y0,x1,y1=pbox
    bitmap=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGRA);raw.FPDFBitmap_FillRect(bitmap,0,0,w,h,0);active(handle,True)
    try:
        raw.FPDF_RenderPageBitmap(bitmap,page,0,0,w,h,0,0);view=bitmap.to_numpy();crop=view[y0:y1,x0:x1];outside=int(np.count_nonzero(view[:,:,3]))-int(np.count_nonzero(crop[:,:,3]));rgba=crop[:,:,[2,1,0,3]].copy()
    finally:active(handle,False);bitmap.close()
    return rgba,outside

def full_text_set_reference(page,handles,pbox,config):
    """Closed native text set, original page paint order, one complete alpha render."""
    W,H=page.get_size();s=config.render_scale;w,h=math.ceil(W*s),math.ceil(H*s);x0,y0,x1,y1=pbox
    bitmap=pdfium.PdfBitmap.new_native(w,h,format=raw.FPDFBitmap_BGRA);raw.FPDFBitmap_FillRect(bitmap,0,0,w,h,0)
    for handle in handles:active(handle,True)
    try:
        raw.FPDF_RenderPageBitmap(bitmap,page,0,0,w,h,0,0);view=bitmap.to_numpy();crop=view[y0:y1,x0:x1];outside=int(np.count_nonzero(view[:,:,3]))-int(np.count_nonzero(crop[:,:,3]));rgba=crop[:,:,[2,1,0,3]].copy()
    finally:
        for handle in handles:active(handle,False)
        bitmap.close()
    return rgba,outside
