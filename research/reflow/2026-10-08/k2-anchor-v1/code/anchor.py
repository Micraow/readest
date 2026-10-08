"""One frozen source-identity/interval-anchoring experiment. No semantic-text generation."""
from helpers import *
import fitz,hashlib
B=pathlib.Path(__file__).resolve().parents[1]
def clamp(box,w,h,pad=0):return [max(0,math.floor(box[0])-pad),max(0,math.floor(box[1])-pad),min(w,math.ceil(box[2])+pad),min(h,math.ceil(box[3])+pad)]
def main(spec):
    t=time.monotonic();key=spec['key'];P=pathlib.Path(spec['prior_dir']);im=Image.open(P/'inputs'/(key+'.png')).convert('RGB');w,h=im.size
    arr=np.asarray(im);ink=np.any(arr<255,2);integ=np.zeros((h+1,w+1),np.uint32);integ[1:,1:]=ink.cumsum(0,dtype=np.uint32).cumsum(1,dtype=np.uint32)
    def ink_count(box):
      a,b,c,d=clamp(box,w,h)
      return int(integ[d,c])+int(integ[b,a])-int(integ[b,c])-int(integ[d,a]) if c>a and d>b else 0
    def common_ink(a,b):return ink_count([max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]) if intersects(a,b) else 0
    raw=json.loads((P/'inputs'/(key+'-rawdict.json')).read_text());glyphs=[];blocks=[]
    for bi,block in enumerate(raw['blocks']):
      gs=[]
      for li,line in enumerate(block.get('lines',[])):
       for si,span in enumerate(line.get('spans',[])):
        for ci,c in enumerate(span.get('chars',[])):
         if c['c'].strip():
          g={'id':f'{bi}:{li}:{si}:{ci}','block_id':bi,'line_id':f'{bi}:{li}','bbox':clamp([v*4 for v in c['bbox']],w,h),'text':c['c']};glyphs.append(g);gs.append(g)
      if gs:blocks.append({'id':bi,'bbox':clamp([v*4 for v in block['bbox']],w,h),'glyphs':gs})
    previous=json.loads((P/'output'/(key+'-composition.json')).read_text());baseline=json.loads((P/'output'/(key+'-baseline.json')).read_text())
    maps=baseline['maps'];ordered=sorted(range(len(maps)),key=lambda i:(maps[i]['target_xywh'][1],maps[i]['target_xywh'][0],i));ordinal={mi:j for j,mi in enumerate(ordered)}
    map_boxes=[]
    for mp in maps:
      x,y,mw,mh=mp['source_xywh'];map_boxes.append([x,y,x+mw,y+mh])
    nodes=[];events=[]
    for r in previous['regions']:
      if r['id']==0:continue
      nodes.append({'bbox':r['bbox'][:],'labels':r['labels'][:],'reuse_id':r['id'] if r['mode']=='candidate_word_reflow' else None,'parent_evidence':[f'detector-component:{r["id"]}'],'mode':r['mode'],'initial_region_id':r['id']})
    # Protected math may acquire unassigned material from the same native block,
    # only when that entire block fits the pre-existing formula vertical band.
    # A native block is evidence, not semantic ground truth.
    for node in nodes:
      if not ('formula' in node['labels'] or len(set(node['labels']))>1):continue
      initial=node['bbox'][:];selected=[]
      for block in blocks:
        if not any(common_ink(g['bbox'],initial)>0 for g in block['glyphs']):continue
        if 'formula' in node['labels'] and not (initial[1]<=block['bbox'][1] and block['bbox'][3]<=initial[3]):continue
        selected.append(block)
      for block in selected:
        node['bbox']=union(node['bbox'],block['bbox']);node['parent_evidence'].append(f'native-block:{block["id"]}')
      if node['bbox']!=initial:
        node['mode']='protected_parent';node['reuse_id']=None;events.append({'action':'native-parent-extension','labels':node['labels'],'before':initial,'after':node['bbox'],'evidence':node['parent_evidence'][:]})
    def owned_mask():
      mask=np.zeros((h,w),bool)
      for n in nodes:
        a,b,c,d=n['bbox'];mask[b:d,a:c]=True
      return mask
    occupied=owned_mask()
    # Unknown text is preserved with its complete native parent, never in a tail atlas.
    for block in blocks:
      a,b,c,d=block['bbox']
      if np.any(ink[b:d,a:c]&~occupied[b:d,a:c]):
        nodes.append({'bbox':block['bbox'][:],'labels':['unknown_native_block'],'reuse_id':None,'mode':'protected_parent','parent_evidence':[f'native-block:{block["id"]}']});occupied[b:d,a:c]=True
    # Non-text native paint objects may explain still-unassigned ink. No image OCR.
    page=fitz.open(spec['pdf'])[spec['pdf_page_1based']-1]
    for pi,paint in enumerate(page.get_bboxlog()):
      typ,box=paint[:2]
      if typ not in {'fill-image','fill-path','stroke-path','fill-shade'}:continue
      box=clamp([v*4 for v in box],w,h,pad=4);a,b,c,d=box
      if c>a and d>b and np.any(ink[b:d,a:c]&~occupied[b:d,a:c]):
        nodes.append({'bbox':box,'labels':['unknown_native_paint'],'reuse_id':None,'mode':'protected_parent','parent_evidence':[f'paint:{pi}:{typ}']});occupied[b:d,a:c]=True
    unexplained=int((ink&~occupied).sum());failure=None
    if unexplained:failure=f'{unexplained} source ink pixels lack a native parent'
    def set_anchor(node):
      members=[g for g in glyphs if common_ink(node['bbox'],g['bbox'])>0]
      support=set()
      # Join source glyph/line membership with actual ink intersections, not map centres.
      # The complete parent ink also includes its native non-text paint objects.
      for j,mb in enumerate(map_boxes):
        if common_ink(node['bbox'],mb)>0:support.add(j)
      node['glyph_ids']=[g['id'] for g in members];node['source_line_ids']=sorted(set(g['line_id'] for g in members));node['support_map_ids']=sorted(support)
      if support:node['anchor_interval']=[min(ordinal[j] for j in support),max(ordinal[j] for j in support)]
      else:node['anchor_interval']=None
    def combine(i,j,reason):
      a,b=nodes[i],nodes[j];merged={'bbox':union(a['bbox'],b['bbox']),'labels':sorted(set(a['labels']+b['labels'])),'reuse_id':None,'mode':'protected_parent','parent_evidence':a['parent_evidence']+b['parent_evidence']}
      events.append({'action':reason,'left':a['bbox'],'right':b['bbox'],'merged':merged['bbox']});nodes[i]=merged;nodes.pop(j)
    # Each merge reduces the node count: finite coarsening, no threshold tuning.
    while not failure:
      changed=False
      for i in range(len(nodes)):
       for j in range(i+1,len(nodes)):
        if intersects(nodes[i]['bbox'],nodes[j]['bbox']):combine(i,j,'overlapping-source-parents');changed=True;break
       if changed:break
      if changed:continue
      for n in nodes:set_anchor(n)
      if any(n['anchor_interval'] is None and ink_count(n['bbox']) for n in nodes):failure='A content parent has no source-supported k2 interval';break
      nodes=[n for n in nodes if n['anchor_interval'] is not None]
      for i in range(len(nodes)):
       for j in range(i+1,len(nodes)):
        a,b=nodes[i]['anchor_interval'],nodes[j]['anchor_interval']
        if max(a[0],b[0])<=min(a[1],b[1]):combine(i,j,'interleaving-or-shared-output-interval');changed=True;break
       if changed:break
      if not changed:break
    if not failure and len(nodes)==1 and ink_count(nodes[0]['bbox'])==int(ink.sum()):failure='All content coarsened into one uncertain parent; preserve entire original page'
    output_nodes=[]
    if failure:
      scale=min(.5,390/w);out=im.resize((round(w*scale),round(h*scale)),Image.Resampling.LANCZOS)
      output_nodes=[({'bbox':[0,0,w,h],'mode':'whole_page_original_failure','labels':['original_page'],'source_ink':int(ink.sum()),'parent_evidence':['original PDF page'],'anchor_interval':None},out)]
    else:
      nodes.sort(key=lambda n:n['anchor_interval'][0]);prev_by_id={r['id']:r for r in previous['regions']}
      for n in nodes:
        n['source_ink']=ink_count(n['bbox'])
        if n['reuse_id'] is not None:
          r=prev_by_id[n['reuse_id']];out=Image.open(P/'output'/f'{key}-region-{r["id"]:02}.ppm').copy();y=r['trimmed_output_top'];out=out.crop((0,y,390,y+r['target_size'][1]));n['mode']='candidate_word_reflow'
        else:
          crop=im.crop(n['bbox']);scale=min(.5,390/crop.width);out=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS);n['display_scale']=scale
        output_nodes.append((n,out))
    height=sum(out.height+24 for n,out in output_nodes)+20;canvas=Image.new('RGB',(390,height),'white');draw=ImageDraw.Draw(canvas);y=8;owner=np.zeros((h,w),np.uint16)
    for idx,(n,out) in enumerate(output_nodes,1):
      n['id']=idx;draw.text((4,y),f"{idx} {n['mode']}",fill=(100,100,100));y+=16;canvas.paste(out,(0,y));n['target_y']=y;n['target_size']=list(out.size);y+=out.height+8;a,b,c,d=n['bbox'];owner[b:d,a:c]+=1
    names=tiles(canvas,key+'-anchored');np.save(B/'output'/(key+'-owner.npy'),owner)
    r={'key':key,'partition':spec['partition'],'failure':failure,'anchoring_constraints_satisfied':failure is None,'all_source_ink':int(ink.sum()),'uncovered_source_ink':int((ink&(owner==0)).sum()),'multiply_owned_source_ink':int((ink&(owner>1)).sum()),'candidate_reflow_source_ink':sum(n['source_ink'] for n,out in output_nodes if n['mode']=='candidate_word_reflow'),'protected_source_ink':sum(n['source_ink'] for n,out in output_nodes if n['mode']!='candidate_word_reflow'),'unexplained_before_page_fallback':unexplained,'nodes':[n for n,out in output_nodes],'coarsening_events':events,'tiles':names,'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'warning':'Intervals preserve the source-supported k2 sequence. They do not make native PDF blocks semantic truth or certify author reading order; visual verification is mandatory.'}
    (B/'output'/(key+'-anchor.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2));print({k:v for k,v in r.items() if k not in ['nodes','coarsening_events']},flush=True)
    return r
if __name__=='__main__':
    if (B/'RUN-STARTED.json').exists():raise SystemExit('Frozen round already started: no automatic rerun')
    registry=json.loads((B/'INPUT-FREEZE.json').read_text());(B/'RUN-STARTED.json').write_text(json.dumps({'epoch':time.time(),'inputs':[s['key'] for s in registry['inputs']]}))
    results=[]
    for s in registry['inputs']:
      if s.get('blocked'):continue
      r=main(s);results.append({k:v for k,v in r.items() if k not in ['nodes','coarsening_events']})
      if r['seconds']>60:break
    (B/'RUN-RESULTS.json').write_text(json.dumps(results,indent=2))
