import pathlib,json,numpy as np
B=pathlib.Path(__file__).resolve().parents[1];P=B.parent/'stroke-object-batch-v1';ref=json.loads((P/'REFERENCE-FREEZE.json').read_text())['inputs'];model={r['key']:r for r in json.loads((B/'RUN-RESULT.json').read_text())['rows']};rows=[]
for inp in json.loads((P/'INPUT-FREEZE.json').read_text())['inputs']:
 key=inp['key'];boxes=json.loads((P/'output'/(key+'-detector.json')).read_text())['res']['boxes'];selected={i:x for i,x in enumerate(boxes) if x['score']>=.5};raw=json.loads((P/'inputs'/(key+'-rawdict.json')).read_text());geo=json.loads((P/'output'/(key+'-result.json')).read_text());width=geo['paint_guard']['size'][0];height=geo['paint_guard']['size'][1];columns=geo['columns'];cut=columns.get('cut')
 def lane(b):
  if columns['count']==1:return 0
  if b[0]<cut-.15*width and b[2]>cut+.15*width:return -1
  return 0 if (b[0]+b[2])/2<cut else 1
 spans=[x['coordinate'] for x in selected.values() if lane(x['coordinate'])==-1]
 def rank(x):
  b=x['coordinate'];col=lane(b);band=sum(s[3]<=b[1] for s in spans)
  if x['label'] in {'header','footer','number'} and b[3]<.1*height:return (-1,0,0,b[1],b[0])
  if x['label'] in {'header','footer','number'} and b[1]>.9*height:return (len(spans)+2,0,0,b[1],b[0])
  return (band,0 if col!=-1 else 2,col,b[1],b[0])
 gr={i:k for k,i in enumerate(sorted(selected,key=lambda i:rank(selected[i])))};mr={i:k for k,i in enumerate(model[key]['model_order_detector_ids'])};units=[]
 for u in ref[key]['complete_body_units']:
  points=[]
  for gid in u['glyph_ids']:
   bi,li,si,ci=map(int,gid.split(':'));b=raw['blocks'][bi]['lines'][li]['spans'][si]['chars'][ci]['bbox'];points.append(((b[0]+b[2])*2,(b[1]+b[3])*2))
  points=np.array(points);scores=[]
  for i,x in selected.items():
   a,b,c,d=x['coordinate'];scores.append((int(((points[:,0]>=a)&(points[:,0]<=c)&(points[:,1]>=b)&(points[:,1]<=d)).sum()),i))
  n,i=max(scores);fraction=n/len(points);units.append({'id':u['id'],'proposal':i if fraction>=.9 else None,'coverage':fraction,'proposal_label':selected[i]['label']})
 pairs=[];unscorable=0
 for i in range(len(units)):
  for j in range(i+1,len(units)):
   a=units[i]['proposal'];b=units[j]['proposal']
   if a is None or b is None or a==b:unscorable+=1;continue
   pairs.append({'units':[units[i]['id'],units[j]['id']],'proposal_ids':[a,b],'geometric_wrong':gr[a]>gr[b],'learned_wrong':mr[a]>mr[b]})
 rows.append({'key':key,'partition':inp['partition'],'complete_units':len(units),'units_with_single_candidate90pct':sum(u['proposal'] is not None for u in units),'all_unit_pairs':len(units)*(len(units)-1)//2,'scored_pairs':len(pairs),'unscorable_pairs':unscorable,'geometric_pair_errors':sum(p['geometric_wrong'] for p in pairs),'learned_pair_errors':sum(p['learned_wrong'] for p in pairs),'units':units,'error_pairs':[p for p in pairs if p['geometric_wrong'] or p['learned_wrong']],'geometry_order_detector_ids':sorted(gr,key=gr.get),'model_order_detector_ids':model[key]['model_order_detector_ids']})
(B/'ORDER-EVALUATION.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:v for k,v in r.items() if k not in ['units','error_pairs','geometry_order_detector_ids','model_order_detector_ids']} for r in rows],indent=2))
