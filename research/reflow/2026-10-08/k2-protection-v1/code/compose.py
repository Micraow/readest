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
summaries=[]
for spec in json.loads((B/'INPUT-FREEZE.json').read_text())['inputs']:
    started=time.monotonic();key=spec['key'];im=Image.open(B/'inputs'/(key+'.png')).convert('RGB');w,h=im.size
    baseline,bm,boff,btime=k2(im,key+'-baseline');baseline_tiles=tiles(baseline,key+'-baseline')
    raw=json.loads((B/'inputs'/(key+'-rawdict.json')).read_text());glyphs=[]
    for block in raw['blocks']:
      for line in block.get('lines',[]):
       for span in line.get('spans',[]):
        for c in span.get('chars',[]):
         if c['c'].strip():glyphs.append([v*4 for v in c['bbox']])
    boxes=json.loads((B/'output'/(key+'-detector.json')).read_text())['res']['boxes'];regions=[]
    for i,p in enumerate(boxes):
      if p['score']<.5:continue
      x0,y0,x1,y1=p['coordinate'];r=[max(0,math.floor(x0)-4),max(0,math.floor(y0)-4),min(w,math.ceil(x1)+4),min(h,math.ceil(y1)+4)]
      original=r[:]
      # Close the proposal over complete intersecting native glyph boxes.
      changed=True;steps=0
      while changed and steps<=len(glyphs):
        changed=False;steps+=1
        for g in glyphs:
          if intersects(r,g):
            nr=union(r,[max(0,math.floor(g[0])),max(0,math.floor(g[1])),min(w,math.ceil(g[2])),min(h,math.ceil(g[3]))])
            if nr!=r:r=nr;changed=True
      regions.append({'ids':[i],'labels':[p['label']],'min_score':p['score'],'bbox':r,'initial_bbox':original,'expanded':r!=original})
    # Formula labels and formula-number labels on the same source row form an atom.
    for a in regions:
      if a['labels']!=['formula_number']:continue
      compatible=[]
      for j,f in enumerate(regions):
        if 'formula' not in f['labels']:continue
        A=a['bbox'];F=f['bbox'];over=min(A[3],F[3])-max(A[1],F[1])
        if over>0.5*min(A[3]-A[1],F[3]-F[1]):compatible.append((abs((A[0]+A[2])-(F[0]+F[2])),j))
      if compatible:
        f=regions[min(compatible)[1]];f['bbox']=union(f['bbox'],a['bbox']);f['ids']+=a['ids'];f['labels']+=a['labels'];a['ids']=[]
    regions=[r for r in regions if r['ids']]
    # Merge every overlapping proposal. Conflicting labels prohibit text reflow.
    changed=True
    while changed:
      changed=False
      for i in range(len(regions)):
       for j in range(i+1,len(regions)):
        if intersects(regions[i]['bbox'],regions[j]['bbox']):
          a,b=regions[i],regions[j];a['bbox']=union(a['bbox'],b['bbox']);a['ids']+=b['ids'];a['labels']+=b['labels'];a['min_score']=min(a['min_score'],b['min_score']);a['expanded']=True;regions.pop(j);changed=True;break
       if changed:break
    owner=np.zeros((h,w),np.uint16);items=[];global_maps=[]
    for idx,r in enumerate(regions,1):
      x0,y0,x1,y1=r['bbox'];owner[y0:y1,x0:x1]=idx;crop=im.crop(r['bbox']);labels=set(r['labels']);r['id']=idx
      ranks=[]
      for mp in bm['maps']:
        x,y,mw,mh=mp['source_xywh'];cx=x+mw/2;cy=y+mh/2
        if x0<=cx<x1 and y0<=cy<y1:ranks.append(mp['target_xywh'][1])
      r['rank']=min(ranks) if ranks else 1e9+y0;r['rank_evidence']='baseline k2 map order; not trusted as semantic truth'
      r['section']='auxiliary' if labels<=AUX else 'floats' if labels<=FLOAT else 'main'
      r['source_ink']=int(np.any(np.asarray(crop)<255,2).sum());r['mode']='protected_original';r['failure_reason']=None
      if labels<=TEXT:
        out,rm,off,dt=k2(crop,f'{key}-region-{idx:02}');check=coverage(crop,rm['maps']);r['k2_seconds']=dt;r['k2_coverage']=check
        if check['unmapped_ink']==0 and check['multiply_mapped_ink']==0:
          r['mode']='candidate_word_reflow';r['maps']=rm['maps'];r['trimmed_output_top']=off
        else:r['failure_reason']='source map integrity guard rejected reflow'
      elif len(labels)>1 and not labels<={'formula','formula_number'}:r['failure_reason']='overlap or mixed-role component: conservatively protected'
      if r['mode']!='candidate_word_reflow':
        scale=min(.5,390/crop.width);out=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS)
        r['display_scale']=scale;r['maps']=[]
      items.append((r,out))
    # Unassigned ink remains in a masked original-page panel, never counted as reflow.
    a=np.asarray(im).copy();remaining=(owner==0)&np.any(a<255,2);residual_ink=int(remaining.sum())
    if residual_ink:
      a[owner>0]=255;ys,xs=np.where(remaining);box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
      crop=Image.fromarray(a).crop(box);scale=min(.5,390/crop.width);out=crop.resize((round(crop.width*scale),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS)
      items.append(({'id':0,'bbox':box,'labels':['unassigned_source'],'mode':'refused_unassigned_original','section':'unassigned','rank':0,'source_ink':residual_ink,'failure_reason':'No confident proposal owns this source ink','maps':[]},out))
    items.sort(key=lambda z:({'main':0,'floats':1,'auxiliary':2,'unassigned':3}[z[0]['section']],z[0]['rank']))
    height=sum(z[1].height+24 for z in items)+20;canvas=Image.new('RGB',(390,height),'white');draw=ImageDraw.Draw(canvas);y=8
    for r,out in items:
      draw.text((4,y),f"{r['id']} {r['section']} {r['mode']}",fill=(100,100,100));y+=16;canvas.paste(out,(0,y));r['target_y']=y;r['target_size']=list(out.size);y+=out.height+8
    candidate_tiles=tiles(canvas,key+'-protected');np.save(B/'output'/(key+'-source-owner.npy'),owner)
    ink=np.any(np.asarray(im)<255,2)
    result={'key':key,'total_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'baseline_coverage':coverage(im,bm['maps']),'all_source_ink':int(ink.sum()),'candidate_reflow_source_ink':sum(r['source_ink'] for r,o in items if r['mode']=='candidate_word_reflow'),'protected_or_unassigned_source_ink':sum(r['source_ink'] for r,o in items if r['mode']!='candidate_word_reflow'),'unassigned_source_ink':residual_ink,'source_partition_no_overlap':True,'regions':[r for r,o in items],'baseline_tiles':baseline_tiles,'candidate_tiles':candidate_tiles,'warning':'Candidate-reflow eligibility and source ownership are not scientific fidelity or actual usable reflow.'}
    (B/'output'/(key+'-composition.json')).write_text(json.dumps(result,indent=2));summaries.append({k:v for k,v in result.items() if k!='regions'});print(summaries[-1],flush=True)
    if result['total_seconds']>60:raise SystemExit('Per-page 60s budget exceeded; do not process additional pages')
(B/'COMPOSITION-METRICS.json').write_text(json.dumps(summaries,indent=2))
