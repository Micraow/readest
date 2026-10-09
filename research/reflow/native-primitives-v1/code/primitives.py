"""Seed a complete visible native divider only through unique footnote context."""
import math
import numpy as np
import fitz
from scipy.ndimage import label,find_objects
from masks import partition

def divider_seeds(page,pix,scale,rgb,nodes,font,raster_box):
 owners,check=partition(rgb,[n['bbox'] for n in nodes]);unknown=np.any(rgb!=255,axis=2)&(owners==0);cc,count=label(unknown,structure=np.ones((3,3),np.uint8));events=[]
 if not count:return events
 strokes=[]
 for d in page.get_drawings():
  if d['type']!='s' or len(d['items'])!=1 or d['items'][0][0]!='l' or not d.get('color') or min(d['color'])>.99:continue
  a,b=d['items'][0][1:];a=a*page.rotation_matrix*fitz.Matrix(scale,scale);b=b*page.rotation_matrix*fitz.Matrix(scale,scale);x0,x1=sorted([a.x-pix.x,b.x-pix.x]);y=(a.y+b.y)/2-pix.y;thickness=d['width']*scale
  if abs(a.y-b.y)>1e-4 or x1-x0<5*font or thickness>.1*font:continue
  strokes.append((x0,x1,y,thickness,d['seqno']))
 for i,slices in enumerate(find_objects(cc),1):
  if slices is None:continue
  sy,sx=slices;box=[sx.start,sy.start,sx.stop,sy.stop];part=cc[sy,sx]==i;ys,xs=np.where(part);xs=xs+sx.start;ys=ys+sy.start
  # An ambiguous component already touching semantic seeds cannot be reassigned here.
  touched=False
  for n in nodes:
   a,b,c,d=n['bbox'];a=max(a,sx.start);b=max(b,sy.start);c=min(c,sx.stop);d=min(d,sy.stop)
   if c>a and d>b and np.any(cc[b:d,a:c]==i):touched=True;break
  if touched:continue
  candidates=[]
  for x0,x1,y,t,seq in strokes:
   if xs.min()<x0-1 or xs.max()+1>x1+1 or np.max(abs(ys+.5-y))>t/2+1:continue
   for j,n in enumerate(nodes):
    if set(n['labels'])!={'footnote'}:continue
    a,b,c,d=n['bbox'];gap=b-box[3];over=min(c,box[2])-max(a,box[0])
    if not (0<=gap<=2*font and over>=.5*(box[2]-box[0])):continue
    new=[min(a,box[0]),min(b,box[1]),max(c,box[2]),max(d,box[3])]
    if any(k!=j and min(new[2],m['bbox'][2])>max(new[0],m['bbox'][0]) and min(new[3],m['bbox'][3])>max(new[1],m['bbox'][1]) for k,m in enumerate(nodes)):continue
    candidates.append((j,seq,new))
  if len(candidates)==1:
   j,seq,new=candidates[0];nodes[j]['bbox']=new;nodes[j]['evidence'].append(f'unique-native-footnote-divider:{seq}');events.append({'native_seqno':seq,'component_pixels':int(part.sum()),'semantic_parent':j,'kind':'footnote_divider'})
 return events
