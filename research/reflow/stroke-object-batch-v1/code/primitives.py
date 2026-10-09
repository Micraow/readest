"""Retain uniquely supported isolated native strokes as unclassified source objects.
No detector footnote label is required; broad fills never acquire semantic ownership.
"""
import numpy as np
import fitz
from scipy.ndimage import label,find_objects
from masks import partition

def divider_seeds(page,pix,scale,rgb,nodes,font,raster_box):
 owners,_=partition(rgb,[n['bbox'] for n in nodes]);unknown=np.any(rgb!=255,axis=2)&(owners==0);cc,_=label(unknown,structure=np.ones((3,3),np.uint8));strokes=[];events=[]
 for d in page.get_drawings():
  if d['type']!='s' or len(d['items'])!=1 or d['items'][0][0]!='l' or not d.get('color') or min(d['color'])>.99:continue
  a,b=d['items'][0][1:];a=a*page.rotation_matrix*fitz.Matrix(scale,scale);b=b*page.rotation_matrix*fitz.Matrix(scale,scale);a=np.array([a.x-pix.x,a.y-pix.y]);b=np.array([b.x-pix.x,b.y-pix.y]);width=d['width']*scale
  if abs(a[1]-b[1])>1e-4 or np.linalg.norm(a-b)<5*font or width>.1*font:continue
  strokes.append((a,b,width,d['seqno']))
 for i,s in enumerate(find_objects(cc),1):
  if s is None:continue
  sy,sx=s;part=cc[sy,sx]==i;ys,xs=np.where(part);points=np.column_stack((xs+sx.start+.5,ys+sy.start+.5));box=[sx.start,sy.start,sx.stop,sy.stop]
  # A unique source-position slot is required; do not merge a graphic into prose.
  if any(min(box[2],n['bbox'][2])>max(box[0],n['bbox'][0]) and min(box[3],n['bbox'][3])>max(box[1],n['bbox'][1]) for n in nodes):continue
  matches=[]
  for a,b,width,seq in strokes:
   v=b-a;t=np.clip(((points-a)@v)/(v@v),0,1);distance=np.linalg.norm(points-(a+t[:,None]*v),axis=1)
   if np.max(distance)<=width/2+1:matches.append(seq)
  if len(matches)!=1:continue
  nodes.append({'bbox':box,'labels':['native_graphic'],'evidence':[f'isolated-native-stroke:{matches[0]}'],'forced_original':True})
  events.append({'native_seqno':matches[0],'component_pixels':int(part.sum()),'kind':'unclassified_native_graphic','source_slot':'nonoverlapping original source position; column/band order still requires audit'})
 return events
