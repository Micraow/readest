"""Pre-inference deterministic source/document split; no performance-based selection."""
import pathlib,json,hashlib,re
from remote_zip import B
if (B/'SELECTION-FREEZE.json').exists():raise SystemExit('Selection already frozen')
extra=json.loads((B/'metadata/extra-entries.json').read_text());seen=set();selected=[]
quotas={'train':[('arxiv_mediumspaced',4),('arxiv_doublespaced',4),('manuals',2),('ann_reports_00_04_fancy',2)],'val':[('arxiv_mediumspaced',2),('arxiv_doublespaced',2),('manuals',1),('ann_reports_00_04_fancy',1)],'test':[('arxiv_two_columns',6),('redbooks',2),('ann_reports_10_14_fancy',2),('chinese_laws',1),('japanese_laws',1)]}
# All previous diagnostic paper identities are excluded from every partition.
old_ids=set()
for f in (B.parent/'readest-research-checkpoint/research/reflow').rglob('*.json'):
 for match in re.finditer(r'arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})',f.read_text()):old_ids.add(match.group(1).replace('.',''))
for split,groups in quotas.items():
 rows=json.loads((B/'metadata'/f'{split}-page-index.json').read_text())['images']
 for collection,n in groups:
  pool=[]
  for r in rows:
   name=r['file_name'].removesuffix('.png');pdf='PDF/'+name+'.pdf';counts=r['class_counts'];digits=re.sub(r'\D','',r['doc_name'])
   if r['collection']!=collection or r['doc_name'] in seen or counts.get('10',0)<2:continue
   if any(identifier in digits for identifier in old_ids):continue
   if collection.startswith('arxiv') and counts.get('3',0)<1:continue
   if pdf not in extra or extra[pdf]['expanded']>2*1024**2:continue
   pool.append(r)
  pool.sort(key=lambda r:hashlib.sha256(('readest-role-pilot-v1:'+r['file_name']).encode()).hexdigest())
  chosen=[]
  for r in pool:
   if r['doc_name'] in seen:continue
   chosen.append(r);seen.add(r['doc_name'])
   if len(chosen)==n:break
  if len(chosen)!=n:raise RuntimeError('Insufficient qualified documents for declared quota '+collection)
  for r in chosen:selected.append({'split':split,**r})
freeze={'selection_rule':'Lexicographic SHA256 seeded filename ordering within declared collection quotas; >=2 annotated Text objects, scientific pages >=1 Formula; native PDF entry <=2MiB; distinct doc_name globally; known diagnostic paper IDs excluded. No output inspection or replacement.','quotas':quotas,'pages':selected,'excluded_old_paper_ids':sorted(old_ids),'split_scope':'Official train/val/test split plus disjoint document names. Test collections absent from train/calibration. Collection is a dataset source/style grouping, not proof of absent near-duplicates or unseen upstream-detector training.','budgets':'Keep all downloads within initial256MiB cumulative range budget and512MiB disk; no full archive.','missing_input_rule':'Selected missing/invalid page stays a recorded failure; no replacement after outputs.'}
(B/'SELECTION-FREEZE.json').write_text(json.dumps(freeze,indent=2));print(json.dumps([{'split':r['split'],'collection':r['collection'],'doc':r['doc_name'],'page':r['page_no'],'formula_objects':r['class_counts'].get('3',0)} for r in selected],indent=2))
