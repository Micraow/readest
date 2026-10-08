"""Frozen column-aware geometry baseline on actual PDF/detector candidates."""
from helpers import *
import fitz,re,sys,hashlib
sys.path.insert(0,str(W/'paint-envelope-v1/code'))
from envelope import inspect,raster_box,PAINT_TYPES
B=pathlib.Path(__file__).resolve().parents[1]
def clamp(b,w,h,pad=0):return [max(0,math.floor(b[0])-pad),max(0,math.floor(b[1])-pad),min(w,math.ceil(b[2])+pad),min(h,math.ceil(b[3])+pad)]
def merged(a,b):return {'bbox':union(a['bbox'],b['bbox']),'labels':sorted(set(a['labels']+b['labels'])),'evidence':a['evidence']+b['evidence'],'forced_original':a.get('forced_original',False) or b.get('forced_original',False)}
def consolidate(nodes):
 while True:
  change=False
  for i in range(len(nodes)):
   for j in range(i+1,len(nodes)):
    if intersects(nodes[i]['bbox'],nodes[j]['bbox']):nodes[i]=merged(nodes[i],nodes[j]);nodes.pop(j);change=True;break
   if change:break
  if not change:return nodes

def infer_columns(lines,width):
 good=[l for l in lines if len(re.findall(r'[A-Za-z]{2,}',l['text']))>=4 and .15*width<l['bbox'][2]-l['bbox'][0]<.65*width]
 if len(good)<10:return {'count':1,'cut':None,'evidence_lines':len(good),'reason':'insufficient two-column support'}
 xs=np.array([(l['bbox'][0]+l['bbox'][2])/2 for l in good]);c=np.array([xs.min(),xs.max()])
 for _ in range(12):
  labels=np.argmin(abs(xs[:,None]-c),axis=1)
  if min(np.bincount(labels,minlength=2))<5:return {'count':1,'cut':None,'evidence_lines':len(good),'reason':'unbalanced support'}
  nc=np.array([np.median(xs[labels==j]) for j in range(2)])
  if np.allclose(nc,c):break
  c=nc
 left=[good[i] for i in range(len(good)) if labels[i]==0];right=[good[i] for i in range(len(good)) if labels[i]==1];le=float(np.median([l['bbox'][2] for l in left]));rs=float(np.median([l['bbox'][0] for l in right]))
 if c[1]-c[0]>.25*width and rs-le>.015*width:return {'count':2,'cut':(le+rs)/2,'gutter':[le,rs],'evidence_lines':len(good),'reason':'two supported line clusters with gap'}
 return {'count':1,'cut':None,'evidence_lines':len(good),'reason':'no separated two-column evidence'}
def lane(box,columns,w):
 if columns['count']==1:return 0
 cut=columns['cut']
 if box[0]<cut-.15*w and box[2]>cut+.15*w:return -1
 return 0 if (box[0]+box[2])/2<cut else 1

def main(spec):
 start=time.monotonic();key=spec['key'];page=fitz.open(B/'inputs'/(key+'.pdf'))[spec['page_1based']-1];pix,paintcheck=inspect(page,4);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);w,h=im.size;arr=np.asarray(im);ink=np.any(arr<255,2);raw=page.get_text('rawdict');lines=[];blocks=[];glyphs=[]
 for bi,b in enumerate(raw['blocks']):
  if b.get('type')!=0:continue
  blocks.append({'id':bi,'bbox':raster_box(b['bbox'],page,pix,4)})
  for li,l in enumerate(b['lines']):
   gs=[];text=''
   for si,s in enumerate(l['spans']):
    for ci,ch in enumerate(s['chars']):
     text+=ch['c']
     if ch['c'].strip():
      g={'id':f'{bi}:{li}:{si}:{ci}','bbox':raster_box(ch['bbox'],page,pix,4),'font_px':s['size']*4};glyphs.append(g);gs.append(g)
   if gs:lines.append({'id':f'{bi}:{li}','bbox':raster_box(l['bbox'],page,pix,4),'text':text,'glyph_ids':[g['id'] for g in gs],'font_px':float(np.median([g['font_px'] for g in gs]))})
 columns=infer_columns(lines,w);font=float(np.median([g['font_px'] for g in glyphs]));det=json.loads((B/'output'/(key+'-detector.json')).read_text())['res']['boxes'];nodes=[]
 for i,p in enumerate(det):
  if p['score']<.5:continue
  box=clamp(p['coordinate'],w,h,4)
  # Close detector boundaries over whole logical glyph boxes.
  while True:
   prev=box[:]
   for g in glyphs:
    if intersects(box,g['bbox']):box=union(box,g['bbox'])
   if prev==box:break
  nodes.append({'bbox':box,'labels':[p['label']],'evidence':[f'detector:{i}'],'forced_original':False})
 relations=[]
 for l in lines:
  if not re.fullmatch(r'\s*\(?\s*[0-9]+[a-z]?\s*\)?\s*',l['text']):continue
  A=l['bbox'];lc=lane(A,columns,w);candidates=[]
  for j,f in enumerate(nodes):
   if 'formula' not in f['labels'] or lane(f['bbox'],columns,w)!=lc:continue
   F=f['bbox'];over=min(A[3],F[3])-max(A[1],F[1]);dy=abs((A[1]+A[3]-F[1]-F[3])/2);gap=max(A[0]-F[2],F[0]-A[2],0)
   if over>=.5*(A[3]-A[1]) or dy<=.6*font:candidates.append((dy+gap*.1,j))
  candidates.sort();accepted=bool(candidates) and (len(candidates)==1 or candidates[1][0]-candidates[0][0]>.5*font)
  row={'source_line':l['id'],'column':lc,'candidate_count':len(candidates),'accepted':accepted}
  if accepted:
   f=nodes[candidates[0][1]];f['bbox']=union(f['bbox'],A);f['labels']=sorted(set(f['labels']+['formula_number']));f['evidence'].append('native-number:'+l['id']);row['formula_detector_ids']=f['evidence'][:]
  relations.append(row)
 # Caption candidates attach only to an unambiguous nearest same-column object.
 for a in nodes:
  if not set(a['labels'])<={'figure_title','table_title','chart_title'}:continue
  A=a['bbox'];compatible=[]
  for j,f in enumerate(nodes):
   if not set(f['labels'])&{'image','table','chart'} or lane(A,columns,w)!=lane(f['bbox'],columns,w):continue
   F=f['bbox'];xover=min(A[2],F[2])-max(A[0],F[0]);gap=max(A[1]-F[3],F[1]-A[3],0)
   if xover>0 and gap<=3*font:compatible.append((gap,j))
  compatible.sort()
  if compatible and (len(compatible)==1 or compatible[1][0]-compatible[0][0]>font):
   f=nodes[compatible[0][1]];f['bbox']=union(f['bbox'],A);f['labels']=sorted(set(f['labels']+a['labels']));f['evidence']+=a['evidence']
 nodes=consolidate(nodes)
 def mask():
  z=np.zeros((h,w),bool)
  for n in nodes:a,b,c,d=n['bbox'];z[b:d,a:c]=True
  return z
 own=mask()
 for b in blocks:
  a,y,c,d=b['bbox']
  if np.any(ink[y:d,a:c]&~own[y:d,a:c]):nodes.append({'bbox':b['bbox'],'labels':['unknown_native_parent'],'evidence':[f'native-block:{b["id"]}'],'forced_original':True});own[y:d,a:c]=True
 for p in paintcheck['paints']:
  a,b,c,d=p['box']
  if np.any(ink[b:d,a:c]&~own[b:d,a:c]):nodes.append({'bbox':p['box'],'labels':['unknown_paint_parent'],'evidence':[f'paint:{p["id"]}:{p["type"]}'],'forced_original':True});own[b:d,a:c]=True
 nodes=consolidate(nodes);failure=None
 if paintcheck['outside_physical_paint_envelopes'] or np.any(ink&~mask()):failure='Unexplained source paint: preserve whole original page'
 for n in nodes:n['lane']=lane(n['bbox'],columns,w)
 # A spanning source object is a band boundary. Ambiguous vertical crossing is refused.
 spans=sorted([n for n in nodes if n['lane']==-1],key=lambda n:n['bbox'][1])
 if any(intersects([0,s['bbox'][1],w,s['bbox'][3]],n['bbox']) for s in spans for n in nodes if n is not s):failure='Spanning object overlaps a column flow; order not proved'
 def order(n):
  band=sum(s['bbox'][3]<=n['bbox'][1] for s in spans)
  if set(n['labels'])<={'number','header','footer'} and n['bbox'][3]<.1*h:return (-1,0,0,n['bbox'][1],n['bbox'][0])
  if set(n['labels'])<={'number','header','footer'} and n['bbox'][1]>.9*h:return (len(spans)+2,0,0,n['bbox'][1],n['bbox'][0])
  return (band,0 if n['lane']!=-1 else 2,n['lane'],n['bbox'][1],n['bbox'][0])
 # In each band, read the left column then the right; the spanning object closes it.
 nodes.sort(key=order)
 baseline,bm,boff,bt=k2(im,key+'-baseline');base_tiles=tiles(baseline,key+'-baseline');items=[]
 if failure:nodes=[{'bbox':[0,0,w,h],'labels':['whole_page_refused'],'evidence':['source page'],'lane':-1,'forced_original':True}]
 for idx,n in enumerate(nodes,1):
  crop=im.crop(n['bbox']);n['id']=idx;n['mode']='protected_original';n['source_ink']=int(np.any(np.asarray(crop)<255,2).sum());n['source_glyph_ids']=[g['id'] for g in glyphs if intersects(n['bbox'],g['bbox'])];n['maps']=[]
  if set(n['labels'])<=TEXT and not n['forced_original']:
   out,met,off,dt=k2(crop,f'{key}-region-{idx:02}');check=coverage(crop,met['maps']);n['k2_coverage']=check
   if check['unmapped_ink']==0 and check['multiply_mapped_ink']==0:n['mode']='candidate_word_reflow';n['maps']=met['maps'];n['trimmed_output_top']=off
  if n['mode']!='candidate_word_reflow':
   scale=min(.5,390/crop.width);out=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS);n['display_scale']=scale
  n['target_size']=list(out.size);items.append((n,out))
 owner=np.zeros((h,w),np.uint16);canvas=Image.new('RGB',(390,sum(o.height+24 for n,o in items)+20),'white');draw=ImageDraw.Draw(canvas);y=8
 for n,out in items:
  draw.text((4,y),f"{n['id']} {n['mode']}",fill=(100,100,100));y+=16;canvas.paste(out,(0,y));n['target_y']=y;y+=out.height+8;a,b,c,d=n['bbox'];owner[b:d,a:c]+=1
 result={'key':key,'columns':columns,'failure':failure,'source_ink':int(ink.sum()),'uncovered_ink':int((ink&(owner==0)).sum()),'duplicate_ink':int((ink&(owner>1)).sum()),'paint_guard':{k:v for k,v in paintcheck.items() if k!='paints'},'all_native_nonspace_glyphs':len(glyphs),'candidate_reflow_native_glyphs':len(set(g for n,o in items if n['mode']=='candidate_word_reflow' for g in n['source_glyph_ids'])),'number_relations':relations,'nodes':[n for n,o in items],'baseline_tiles':base_tiles,'candidate_tiles':tiles(canvas,key+'-column'),'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 (B/'output'/(key+'-result.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['nodes','number_relations']},indent=2));return result
if __name__=='__main__':
 if (B/'RUN-STARTED.json').exists():raise SystemExit('Frozen round already started')
 (B/'RUN-STARTED.json').write_text(json.dumps({'epoch':time.time(),'code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}))
 for s in json.loads((B/'INPUT-FREEZE.json').read_text())['inputs']:
  r=main(s)
  if r['seconds']>60:raise SystemExit('Page budget exceeded')
