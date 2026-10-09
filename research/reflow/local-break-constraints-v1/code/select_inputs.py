import pathlib,json,collections,hashlib,re
B=pathlib.Path(__file__).resolve().parents[1];P=B.parent/'doclaynet-role-pilot-v1'
if (B/'INPUT-SELECTION.json').exists():raise SystemExit('Already selected')
used={r['doc_name'] for r in json.loads((P/'SELECTION-FREEZE.json').read_text())['pages']};oldids=json.loads((P/'SELECTION-FREEZE.json').read_text())['excluded_old_paper_ids'];extra=json.loads((P/'metadata/extra-entries.json').read_text());groups=collections.defaultdict(list)
for split in ['train','val','test']:
 for row in json.loads((P/'metadata'/f'{split}-page-index.json').read_text())['images']:
  if row['doc_name'] in used or any(i in re.sub(r'\D','',row['doc_name']) for i in oldids):continue
  if extra['PDF/'+row['file_name'][:-4]+'.pdf']['expanded']>2*1024**2:continue
  groups[row['doc_name']].append({'official_split':split,**row})
criteria=[('arxiv_mediumspaced',3,False,False),('arxiv_doublespaced',3,False,False),('arxiv_two_columns',1,True,False),('arxiv_two_columns',1,False,True),('redbooks',0,True,False),('chinese_laws',0,False,False)];selected=[]
for index,(collection,formula,picture,table) in enumerate(criteria,1):
 pairs=[]
 for doc,rows in groups.items():
  if doc in used or rows[0]['collection']!=collection:continue
  rows=sorted(rows,key=lambda r:r['page_no'])
  for a,b in zip(rows,rows[1:]):
   if b['page_no']!=a['page_no']+1 or min(a['class_counts'].get('10',0),b['class_counts'].get('10',0))<3:continue
   count=lambda k:a['class_counts'].get(k,0)+b['class_counts'].get(k,0)
   if count('3')<formula or picture and not count('7') or table and not count('9'):continue
   pairs.append((hashlib.sha256(('local-break-v1:'+a['file_name']+b['file_name']).encode()).hexdigest(),doc,a,b))
 if not pairs:raise RuntimeError('Missing eligible adjacent document pair '+collection)
 _,doc,a,b=min(pairs,key=lambda p:p[0]);used.add(doc)
 for offset,row in enumerate([a,b],1):selected.append({'key':f'D{index}-P{offset}','pair':index,'adjacent_page_slot':offset,**row})
freeze={'rule':'Deterministic seeded hash rank of adjacent pairs, collection quotas, both pages>=3Text objects, declared math/figure/table minimum. Native PDF entry<=2MiB. No performance inspection or replacement.','criteria':criteria,'previous_pilot_documents_excluded':30,'pages':selected,'page_number_note':'page_no is official source metadata, not asserted printed page label. Each downloaded PDF contains one selected page.','scope':'Collection identifies a source/style stratum; no source-wide or upstream-model-unseen guarantee.'}
(B/'INPUT-SELECTION.json').write_text(json.dumps(freeze,indent=2));print(json.dumps([{'key':r['key'],'doc':r['doc_name'],'page_no':r['page_no'],'collection':r['collection'],'class_counts':r['class_counts']} for r in selected],indent=2))
