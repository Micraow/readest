"""Source atoms and local geometric dependency closure. No paper-specific rules."""
import collections,json,math,pathlib,re,time,unicodedata,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/"stroke-object-batch-v1/code"))
from compose import infer_columns
import fitz,numpy as np
from scipy.ndimage import label,find_objects
from PIL import Image
SCALE=4
TEXT={'text','abstract','content','reference','paragraph_title','doc_title','figure_title','table_title','chart_title'}
AUX={'header','footer','number','footnote','aside_text','header_image','footer_image'}
OBJECT={'image','table','chart','algorithm'}
MATH=re.compile(r'CMMI|CMSY|CMEX|Math|Symbol|STIX',re.I)
class UF:
 def __init__(self,n):self.p=list(range(n))
 def find(self,a):
  while self.p[a]!=a:self.p[a]=self.p[self.p[a]];a=self.p[a]
  return a
 def join(self,ids):
  ids=list(ids)
  if not ids:return
  r=self.find(ids[0])
  for i in ids[1:]:self.p[self.find(i)]=r

def union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def contains(b,x,y):return b[0]<=x<=b[2] and b[1]<=y<=b[3]
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def area(b):return max(0,b[2]-b[0])*max(0,b[3]-b[1])
def distance(a,b):return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))
def modefont(ws,default=10):
 c=collections.Counter()
 for w in ws:
  if not w['math']:c[round(w['size'],2)]+=sum(x.isalpha() for x in w['text'])
 return c.most_common(1)[0][0] if c and c.most_common(1)[0][1]>0 else default

def native_words(page):
 words=[];aliases={}
 for bi,b in enumerate(page.get_text('rawdict')['blocks']):
  for li,line in enumerate(b.get('lines',[])):
   tokens=[];token=[]
   for si,span in enumerate(line['spans']):
    for ci,ch in enumerate(span['chars']):
     c=ch['c'];r=fitz.Rect(ch['bbox'])*page.rotation_matrix;p=fitz.Point(ch['origin'])*page.rotation_matrix
     g={'char':c,'box':list(r),'origin':[p.x,p.y],'size':span['size'],'font':span['font'],'id':f'{bi}:{li}:{si}:{ci}'}
     if c.isspace():
      if token:tokens.append(token);token=[]
      continue
     wide=unicodedata.east_asian_width(c) in 'WF' and not unicodedata.category(c).startswith('M')
     if token:
      prev=token[-1];gap=p.x-prev['box'][2];split=gap>.22*max(g['size'],prev['size']) or abs(p.y-prev['origin'][1])>.15*max(g['size'],prev['size']) or max(g['size'],prev['size'])/max(.1,min(g['size'],prev['size']))>1.2 or wide or unicodedata.east_asian_width(prev['char']) in 'WF'
      if split:tokens.append(token);token=[]
     token.append(g)
   if token:tokens.append(token)
   for gs in tokens:
    box=union([g['box'] for g in gs]);text=''.join(g['char'] for g in gs);origin=min(g['origin'][0] for g in gs);baseline=float(np.median([g['origin'][1] for g in gs]));size=float(np.median([g['size'] for g in gs]));key=(text,round(origin,2),round(baseline,2),round(size,2),tuple(round(x,2) for x in box))
    ids=[g['id'] for g in gs]
    if key in aliases:words[aliases[key]]['native_ids']+=ids;words[aliases[key]]['native_blocks'].append(bi);continue
    aliases[key]=len(words);words.append({'id':len(words),'text':text,'box':box,'origin':origin,'baseline':baseline,'size':size,'math':any(MATH.search(g['font']) for g in gs),'glyphs':gs,'native_ids':ids,'native_blocks':[bi],'native_line':f'{bi}:{li}','advance':max(.1,box[2]-origin)})
 return words

def build(page,predictions):
 started=time.monotonic();pix=page.get_pixmap(matrix=fitz.Matrix(SCALE,SCALE),alpha=False,colorspace=fitz.csRGB);rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).copy();ink=np.any(rgb!=255,axis=2);cc,count=label(ink,np.ones((3,3),np.uint8));slices=find_objects(cc);pixels=np.bincount(cc.ravel());words=native_words(page);body=modefont(words);parents={};det=[];dummy=[];associations=[];edges=[];ambiguous=[]
 for i,p in enumerate(predictions):
  if p['score']<.5:continue
  box=[v/SCALE for v in p['coordinate']];det.append({'id':i,'label':p['label'],'box':box,'score':p['score']})
  if p['label'] in TEXT|AUX|OBJECT:parents['d'+str(i)]={'id':'d'+str(i),'box':box,'role':p['label'],'score':p['score']}
 for w in words:
  candidates=[p for p in det if p['label'] in OBJECT and contains(p['box'],(w['box'][0]+w['box'][2])/2,(w['box'][1]+w['box'][3])/2)]
  if not candidates:candidates=[p for p in det if p['label'] in TEXT|AUX and contains(p['box'],(w['box'][0]+w['box'][2])/2,(w['box'][1]+w['box'][3])/2)]
  if candidates:best=min(candidates,key=lambda p:(area(p['box']),-p['score']));w['parent']='d'+str(best['id'])
  else:
   key='n'+str(w['native_blocks'][0]);w['parent']=key
   if key not in parents:parents[key]={'id':key,'box':w['box'][:],'role':'unknown_native','score':0}
   else:parents[key]['box']=union([parents[key]['box'],w['box']])
 for p in parents.values():p['font']=modefont([w for w in words if w['parent']==p['id']],body)
 # Figure/table rectangles propose support; overlapping rectangles never merge parents.
 for p in parents.values():
  if p['role'] in OBJECT:dummy.append({'box':p['box'][:],'parent':p['id'],'role':p['role'],'word_ids':[w['id'] for w in words if w['parent']==p['id']]})
 for f in [p for p in det if p['label']=='formula']:
  members=[w for w in words if contains(f['box'],(w['box'][0]+w['box'][2])/2,(w['box'][1]+w['box'][3])/2)];numbers=[]
  for w in members:
   if not re.fullmatch(r'\((?:\d+(?:\.\d+)*(?:[a-z])?|[IVX]+)\)',w['text']):continue
   rest=[z for z in members if z is not w]
   if not rest:continue
   core=union([z['box'] for z in rest]);gap=max(w['box'][0]-core[2],core[0]-w['box'][2],0)
   if gap>body and min(w['box'][3],core[3])>max(w['box'][1],core[1]):numbers.append(w)
  corewords=[w for w in members if w not in numbers];box=union([w['box'] for w in corewords]) if corewords else f['box'][:]
  # Detached equation identifiers are association candidates, not geometry edges.
  for w in words:
   if w in members or not re.fullmatch(r'\((?:\d+(?:\.\d+)*(?:[a-z])?|[IVX]+)\)',w['text']):continue
   y=(w['box'][1]+w['box'][3])/2;compatible=[]
   for other in [q for q in det if q['label']=='formula']:
    q=other['box'];dy=max(q[1]-y,y-q[3],0);gap=max(w['box'][0]-q[2],q[0]-w['box'][2],0)
    corridor=[min(w['box'][2],q[2]),y-.3*body,max(w['box'][0],q[0]),y+.3*body]
    intervening=any(z is not w and z not in members and sum(c.isalpha() for c in z['text'])>=2 and overlap(z['box'],corridor) for z in words)
    if dy<=.25*body and gap>body and not intervening:compatible.append(other['id'])
   if compatible==[f['id']]:numbers.append(w)
  ps=collections.Counter(w['parent'] for w in corewords);parent=ps.most_common(1)[0][0] if ps else 'f'+str(f['id']);intext=parent in parents and parents[parent]['role'] in TEXT
  outside=[w for w in words if w not in members and w['parent']==parent and not w['math'] and sum(c.isalpha() for c in w['text'])>=2 and box[1]-.1*body<=w['baseline']<=box[3]+.1*body]
  inline=bool(outside) and intext
  for w in corewords+numbers:w['math_anchor_y']=None if inline else (box[1]+box[3])/2
  if not intext:
   parent='f'+str(f['id']);parents[parent]={'id':parent,'box':box,'role':'formula','font':body,'score':f['score']}
   for w in corewords+numbers:w['parent']=parent
  d={'box':box,'parent':parent,'role':'inline_math' if inline else 'formula','word_ids':[w['id'] for w in corewords],'number_ids':[w['id'] for w in numbers],'display':not inline};dummy.append(d)
  for w in numbers:associations.append({'kind':'formula_number','number':w['id'],'formula_dummy':len(dummy)-1,'geometry_locked':False})
 # Derive supported columns from actual native line extents, not trace sequence.
 linegroups=collections.defaultdict(list)
 for w in words:linegroups[w['native_line']].append(w)
 lines=[{'bbox':union([w['box'] for w in ws]),'text':' '.join(w['text'] for w in sorted(ws,key=lambda w:w['origin']))} for ws in linegroups.values()]
 columns=infer_columns(lines,page.rect.width)
 for w in words:
  w['lane']=0
  if columns['count']==2:
   linebox=union([z['box'] for z in linegroups[w['native_line']]])
   w['lane']=-1 if linebox[0]<columns['cut']-.15*page.rect.width and linebox[2]>columns['cut']+.15*page.rect.width else int((w['box'][0]+w['box'][2])/2>=columns['cut'])
 # A broad native block is not semantic proof that two columns are one paragraph.
 for pid,p in list(parents.items()):
  ws=[w for w in words if w['parent']==pid];lanes={w['lane'] for w in ws}
  if p['role'] in TEXT|{'unknown_native'} and 0 in lanes and 1 in lanes and -1 not in lanes:
   for lane in [0,1]:
    local=[w for w in ws if w['lane']==lane];key=pid+'c'+str(lane);parents[key]={**p,'id':key,'box':union([w['box'] for w in local])}
    for w in local:w['parent']=key
 n=len(words);uf=UF(n+len(dummy))
 for j,d in enumerate(dummy):
  d['id']=n+j;uf.join([d['id']]+d['word_ids']);edges.append({'kind':'object_geometry','nodes':[d['id']]+d['word_ids']})
 # Stable rows use nonblank, ordinary-size, non-math text, not radical origins.
 ordered={};rows_by_parent={}
 for pid,p in parents.items():
  ws=[w for w in words if w['parent']==pid];font=p['font'];rows=[]
  for w in sorted([w for w in ws if w['size']>=.88*font and not w['math']],key=lambda w:w['baseline']):
   near=[r for r in rows if abs(r['y']-w['baseline'])<=.12*font]
   if near:near[0]['members'].append(w['id']);near[0]['y']=float(np.median([words[i]['baseline'] for i in near[0]['members']]))
   else:rows.append({'y':w['baseline'],'members':[w['id']]})
  if not rows:rows=[{'y':float(np.median([w['baseline'] for w in ws])) if ws else p['box'][3],'members':[]}]
  rows.sort(key=lambda r:r['y']);rows_by_parent[pid]=rows
  for w in ws:
   close=[(abs(r['y']-w['baseline']),k) for k,r in enumerate(rows)];close.sort();w['row']=close[0][1]
   if w['size']<.88*font:
    candidates=[z['id'] for z in ws if z is not w and z['size']>=.88*font and abs(z['baseline']-w['baseline'])<=.9*font and z['origin']<=w['origin']+.15*font and -.2*font<=w['origin']-z['box'][2]<=.55*font]
    if not candidates:candidates=[z['id'] for z in ws if z is not w and distance(w['box'],z['box'])<=.45*font]
    if candidates:
     ids=[w['id']]+candidates;uf.join(ids);edges.append({'kind':'script_parent_candidates','nodes':ids})
     if len(candidates)!=1:ambiguous.append(ids)
    else:ambiguous.append([w['id']])
   # CJK closing punctuation and combining marks cannot start a new visual line.
   if unicodedata.category(w['text'][0]) in {'Pe','Pf','Po','Mn','Mc'}:
    previous=[z for z in ws if z['origin']<w['origin'] and abs(z['baseline']-w['baseline'])<=.15*font]
    if previous:uf.join([w['id'],max(previous,key=lambda z:z['origin'])['id']])
  ordered[pid]=[w['id'] for w in sorted(ws,key=lambda w:(w.get('math_anchor_y') if w.get('math_anchor_y') is not None else rows[w['row']]['y'],w['origin'],w['id']))]
 # Per-visible-component support. A touching component is never cut between words.
 holders=[set() for _ in range(count+1)]
 def seed(node,box):
  a,b,c,d=box;a=max(0,math.floor(a*SCALE));b=max(0,math.floor(b*SCALE));c=min(pix.width,math.ceil(c*SCALE));d=min(pix.height,math.ceil(d*SCALE))
  if c>a and d>b:
   for k in np.unique(cc[b:d,a:c]):
    if k:holders[int(k)].add(node)
 for w in words:seed(w['id'],[w['origin'],w['baseline']-.7*w['size'],w['box'][2],w['baseline']+.2*w['size']])
 for d in dummy:seed(d['id'],d['box'])
 unknown=[]
 for k,s in enumerate(slices,1):
  y,x=s;box=[x.start/SCALE,y.start/SCALE,x.stop/SCALE,y.stop/SCALE]
  if not holders[k]:
   # Long isolated rules remain graphic objects unless an object already supported them.
   thin=(box[2]-box[0]>4*(box[3]-box[1]) and box[2]-box[0]>2*body and box[3]-box[1]<.2*body)
   near=[] if thin else [(distance(box,w['box']),w['id']) for w in words];near.sort()
   ids=[i for dist,i in near if dist<=min(.5*body,(near[0][0]+.12*body if near else 0))]
   if ids:holders[k].update(ids);ambiguous.append(ids) if len(ids)>1 else None
   else:unknown.append((k,box));continue
  uf.join(holders[k])
 # Closure preserves the source word order interval; no arbitrary island-size cutoff.
 change=True
 while change:
  before=[uf.find(i) for i in range(n+len(dummy))]
  for ids in ordered.values():
   positions=collections.defaultdict(list)
   for j,i in enumerate(ids):positions[uf.find(i)].append(j)
   for pos in positions.values():
    if len(pos)>1:uf.join(ids[min(pos):max(pos)+1])
  change=before!=[uf.find(i) for i in range(n+len(dummy))]
 return {'rgb':rgb,'cc':cc,'slices':slices,'pixels':pixels,'words':words,'parents':parents,'dummy':dummy,'rows':rows_by_parent,'ordered':ordered,'uf':uf,'holders':holders,'unknown':unknown,'edges':edges,'ambiguous':ambiguous,'associations':associations,'font':body,'columns':columns,'size':[pix.width,pix.height],'seconds':time.monotonic()-started}

def materialize(state,arm):
 words=state['words'];n=len(words);dummy=state['dummy'];uf=UF(n+len(dummy));uf.p=[state['uf'].find(i) for i in range(n+len(dummy))]
 if arm=='B':
  blocks={block for edge in state['ambiguous'] for i in edge if i<n for block in words[i]['native_blocks']}
  for block in blocks:uf.join([w['id'] for w in words if block in w['native_blocks']])
 # Repeat interval closure after B's block rejection to avoid reordering neighbors.
 changed=True
 while changed:
  before=uf.p[:]
  for ids in state['ordered'].values():
   positions=collections.defaultdict(list)
   for j,i in enumerate(ids):positions[uf.find(i)].append(j)
   for ps in positions.values():
    if len(ps)>1:uf.join(ids[min(ps):max(ps)+1])
  changed=before!=[uf.find(i) for i in range(len(uf.p))]
 groups=collections.defaultdict(lambda:{'words':[],'components':[],'dummies':[]})
 for w in words:groups[uf.find(w['id'])]['words'].append(w['id'])
 for d in dummy:groups[uf.find(d['id'])]['dummies'].append(d)
 for k,ids in enumerate(state['holders']):
  if k and ids:groups[uf.find(next(iter(ids)))]['components'].append(k)
 for k,box in state['unknown']:groups['u'+str(k)]={'words':[],'components':[k],'dummies':[],'unknown_box':box}
 atoms=[];assigned=0
 for gid,g in groups.items():
  if not g['components']:continue
  boxes=[]
  for k in g['components']:
   y,x=state['slices'][k-1];boxes.append([x.start,y.start,x.stop,y.stop])
  box=union(boxes);a,b,c,d=box;crop=state['rgb'][b:d,a:c].copy();mask=np.isin(state['cc'][b:d,a:c],g['components']);rgba=np.dstack([crop,(mask*255).astype(np.uint8)]);rgba[~mask,:3]=255;assigned+=int(mask.sum());ws=[words[i] for i in g['words']];parents=collections.Counter(w['parent'] for w in ws);pid=parents.most_common(1)[0][0] if parents else g['dummies'][0]['parent'] if g['dummies'] else 'u'+str(gid)
  parent=state['parents'].get(pid,{'role':'graphic','font':state['font'],'box':[v/SCALE for v in box]});font=parent['font'];ordered=state['ordered'].get(pid,[]);position=min([ordered.index(w['id']) for w in ws if w['id'] in ordered],default=0);row=min([w.get('row',0) for w in ws if w['parent']==pid],default=0);baselines=state['rows'].get(pid,[{'y':d/SCALE}]);baseline=baselines[min(row,len(baselines)-1)]['y'];origin=min([w['origin'] for w in ws],default=a/SCALE);right=max([w['box'][2] for w in ws],default=c/SCALE);objects={v['role'] for v in g['dummies']};role='object' if objects&OBJECT or parent['role']=='formula' else 'island' if len(ws)>1 else 'word';advance=max(right-origin,(c-a)/SCALE if role!='word' else .1)
  atoms.append({'id':str(gid),'parent':pid,'parent_role':parent['role'],'position':position,'source_box':[v/SCALE for v in box],'baseline':baseline,'advance_em':advance/font,'image_width_em':(c-a)/SCALE/font,'height_em':(d-b)/SCALE/font,'descent_em':(d/SCALE-baseline)/font,'left_em':(a/SCALE-origin)/font,'font_reference':font,'role':role,'words':g['words'],'native_ids':[i for w in ws for i in w['native_ids']],'native_blocks':sorted({b for w in ws for b in w['native_blocks']}),'native_text':' '.join(w['text'] for w in sorted(ws,key=lambda z:(z.get('row',0),z['origin']))),'source_ink':int(mask.sum()),'rgba':Image.fromarray(rgba),'component_ids':g['components'],'dummy_ids':[d['id'] for d in g['dummies']],'lanes':sorted({w['lane'] for w in ws}),'parent_ids':sorted(parents),'display_math':any(v.get('display',False) for v in g['dummies']),'number_words':[a['number'] for a in state['associations'] if a['number'] in g['words']],'sort_y':min([w.get('math_anchor_y') if w.get('math_anchor_y') is not None else state['rows'][w['parent']][w['row']]['y'] for w in ws],default=b/SCALE),'ambiguous':any(set(g['words'])&set(e) for e in state['ambiguous'])})
 return atoms,{'arm':arm,'source_ink':int((state['cc']>0).sum()),'assigned_ink':assigned,'unassigned_ink':int((state['cc']>0).sum())-assigned,'duplicate_native_aliases':sum(max(0,len(w['native_blocks'])-1) for w in words),'atoms':len(atoms),'ambiguous_local_sets':len(state['ambiguous']),'ordinary_word_count':len(words),'island_word_count':sum(len(a['words']) for a in atoms if a['role']=='island'),'max_island_words':max([len(a['words']) for a in atoms if a['role']=='island'] or [0])}
