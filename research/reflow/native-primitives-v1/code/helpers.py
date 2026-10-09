import os,pathlib,json,time,math,resource,subprocess
import numpy as np
from PIL import Image,ImageDraw
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent
H=W/'k2-reuse-v2-default/build/k2-reflow-harness'
TEXT={'text','abstract','content','reference'}
FLOAT={'image','table','algorithm','figure_title','table_title','chart','chart_title'}
AUX={'number','footnote','header','footer','aside_text','seal','header_image','footer_image'}
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
def intersects(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def union(a,b):return [min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
def coverage(im,maps):
    a=np.asarray(im);ink=np.any(a<255,2);h,w=ink.shape;c=np.zeros((h,w),np.uint16)
    for m in maps:
      x,y,bw,bh=m['source_xywh'];x0=max(0,math.floor(x+1e-6));y0=max(0,math.floor(y+1e-6));x1=min(w,math.ceil(x+bw-1e-6));y1=min(h,math.ceil(y+bh-1e-6));c[y0:y1,x0:x1]+=1
    return {'source_ink':int(ink.sum()),'unmapped_ink':int((ink&(c==0)).sum()),'multiply_mapped_ink':int((ink&(c>1)).sum())}
def k2(im,key):
    ppm=B/'output'/(key+'-input.ppm');out=B/'output'/(key+'.ppm');met=B/'output'/(key+'.json');im.save(ppm)
    t=time.monotonic();r=subprocess.run(['timeout','--kill-after=1','60',str(H),str(ppm),str(out),str(met)],capture_output=True,text=True)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    m=json.loads(met.read_text());result=Image.open(out).copy();a=np.asarray(result);ys=np.where(np.any(a<255,2))[0]
    y0=max(0,int(ys.min())-8) if len(ys) else 0;y1=min(result.height,int(ys.max())+9) if len(ys) else 1
    return result.crop((0,y0,result.width,y1)),m,y0,time.monotonic()-t
def tiles(im,key):
    im.save(B/'evidence'/(key+'.png'));names=[]
    for i,y in enumerate(range(0,im.height,844)):
      c=Image.new('RGB',(390,844),'white');c.paste(im.crop((0,y,390,min(y+844,im.height))))
      n=f'{key}-tile-{i+1:02}.png';c.save(B/'evidence'/n);names.append(n)
    return names
