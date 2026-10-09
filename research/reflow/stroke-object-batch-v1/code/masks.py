"""Keep final rendered RGB authoritative; paint envelopes never own semantic pixels."""
import numpy as np
from scipy.ndimage import label

def partition(rgb,semantic_boxes):
 ink=np.any(rgb!=255,axis=2);components,count=label(ink,structure=np.ones((3,3),np.uint8));h,w=ink.shape;support=[set() for _ in range(count+1)]
 for owner,box in enumerate(semantic_boxes,1):
  a,b,c,d=box;a=max(0,a);b=max(0,b);c=min(w,c);d=min(h,d)
  if c>a and d>b:
   for cc in np.unique(components[b:d,a:c]):
    if cc:support[int(cc)].add(owner)
 lut=np.zeros(count+1,np.int32);unseeded=[];ambiguous=[]
 for cc in range(1,count+1):
  if len(support[cc])==1:lut[cc]=next(iter(support[cc]))
  elif not support[cc]:unseeded.append(cc)
  else:ambiguous.append(cc)
 owners=lut[components];unknown=ink&(owners==0)
 # Refusal keeps the complete final raster. No hidden source text can be regenerated.
 fallback=bool(unknown.any());restored=np.full_like(rgb,255)
 if fallback:restored[:]=rgb
 else:restored[owners>0]=rgb[owners>0]
 return owners,{'visible_ink':int(ink.sum()),'components':count,'unseeded_components':len(unseeded),'ambiguous_components':len(ambiguous),'unassigned_visible_ink':int(unknown.sum()),'whole_page_refusal':fallback,'changed_rgb_pixels_after_guard':int(np.any(restored!=rgb,axis=2).sum())}
