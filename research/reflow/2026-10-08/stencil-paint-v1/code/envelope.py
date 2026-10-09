"""Physical paint envelopes and exact raster conservation, separate from semantics."""
import math
import fitz
import numpy as np
PAINT_TYPES={'fill-text','stroke-text','fill-path','stroke-path','fill-image','fill-imgmask','fill-shade'}
def raster_box(box,page,pix,scale):
    # All four corners, page rotation, scale, then pixmap's clipped global origin.
    r=fitz.Rect(box)*page.rotation_matrix*fitz.Matrix(scale,scale)
    return [max(0,math.floor(r.x0-pix.x)-1),max(0,math.floor(r.y0-pix.y)-1),min(pix.width,math.ceil(r.x1-pix.x)+1),min(pix.height,math.ceil(r.y1-pix.y)+1)]
def inspect(page,scale=4,clip=None):
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False,clip=clip)
    arr=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3);ink=np.any(arr!=255,axis=2)
    physical=np.zeros(ink.shape,bool);logical=np.zeros(ink.shape,bool);paints=[]
    for i,(typ,box,*_) in enumerate(page.get_bboxlog()):
        if typ not in PAINT_TYPES:continue
        a,b,c,d=raster_box(box,page,pix,scale)
        if c>a and d>b:physical[b:d,a:c]=True;paints.append({'id':i,'type':typ,'box':[a,b,c,d]})
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines',[]):
            for span in line['spans']:
                for ch in span['chars']:
                    a,b,c,d=raster_box(ch['bbox'],page,pix,scale)
                    if c>a and d>b:logical[b:d,a:c]=True
    residual=ink&~physical;fallback=bool(residual.any());owned=physical if not fallback else np.ones(ink.shape,bool)
    # Conservation at original resolution; no resampling or duplicate output ownership.
    reconstructed=np.full_like(arr,255);reconstructed[owned]=arr[owned]
    return pix,{'scale':scale,'pixel_origin':[pix.x,pix.y],'size':[pix.width,pix.height],'paint_objects':len(paints),'source_ink':int(ink.sum()),'outside_logical_glyph_envelopes':int((ink&~logical).sum()),'outside_physical_paint_envelopes':int(residual.sum()),'whole_page_fallback':fallback,'changed_rgb_pixels_after_guard':int(np.any(reconstructed!=arr,axis=2).sum()),'paints':paints,'warning':'Envelopes prove raster containment only; overlaps do not assign semantic ownership or author reading order.'}
