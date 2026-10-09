"""Metadata-only deterministic registration. Never opens a PDF or source image.

The source is the already downloaded official DocLayNet validation COCO metadata.
No upstream-model-unseen claim is possible. This registry is for later evaluation;
input byte hashes must be added before opening outputs, without replacing pages.
"""
import argparse,collections,hashlib,json,pathlib,re,zlib

def nested_docs(value):
 if isinstance(value,dict):
  if isinstance(value.get('doc_name'),str):yield value['doc_name']
  for v in value.values():yield from nested_docs(v)
 elif isinstance(value,list):
  for v in value:yield from nested_docs(v)

def register(metadata,prior,output):
 output=pathlib.Path(output)
 if output.exists():raise SystemExit('Registry already exists; never overwrite a registered holdout.')
 metadata=pathlib.Path(metadata);prior=pathlib.Path(prior);seen=set();paper_ids=set();sources=[]
 for p in prior.rglob('*.json'):
  if 'generic-reflow-v2' in p.parts:continue
  try:
   text=p.read_text();data=json.loads(text)
  except (UnicodeDecodeError,json.JSONDecodeError):continue
  found=set(nested_docs(data));seen.update(found)
  if found:sources.append({'path':str(p.relative_to(prior)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  paper_ids.update(m.replace('.','') for m in re.findall(r'arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})',text))
  if isinstance(data,dict):paper_ids.update(data.get('excluded_old_paper_ids',[]))
 packed=(metadata/'val.deflate').read_bytes();raw=zlib.decompress(packed,-15);data=json.loads(raw)
 entries=json.loads((metadata/'extra-entries.json').read_text());counts=collections.defaultdict(collections.Counter)
 for a in data['annotations']:
  if a.get('precedence',0)==0:counts[a['image_id']][str(a['category_id'])]+=1
 quotas=['faa_regulations','eu_tenders','ann_reports_10_14_fancy','german_laws','arxiv_mediumspaced','arxiv_two_columns'];seed='generic-reflow-v2-20261009-registry-1';pages=[]
 for collection in quotas:
  pool=[]
  for r in data['images']:
   name='PDF/'+r['file_name'].removesuffix('.png')+'.pdf';digits=re.sub(r'\D','',r['doc_name'])
   if r.get('precedence',0)!=0 or r['collection']!=collection or r['doc_name'] in seen or name not in entries:continue
   if any(identifier in digits for identifier in paper_ids):continue
   if counts[r['id']]['10']<2 or entries[name]['expanded']>2*1024**2:continue
   if collection.startswith('arxiv') and counts[r['id']]['3']<1:continue
   pool.append(r)
  if not pool:raise RuntimeError('No page for registered quota '+collection+'; do not silently replace quota.')
  chosen=min(pool,key=lambda r:hashlib.sha256((seed+':'+r['file_name']).encode()).hexdigest());seen.add(chosen['doc_name']);entry=entries['PDF/'+chosen['file_name'].removesuffix('.png')+'.pdf']
  pages.append({'key':'H'+str(len(pages)+1),'official_split':'val','image_id':chosen['id'],'file_name':chosen['file_name'],'doc_name':chosen['doc_name'],'collection':collection,'page_no':chosen['page_no'],'class_counts':dict(counts[chosen['id']]),'archive_pdf_expanded_bytes':entry['expanded'],'archive_pdf_crc32':entry['crc32'],'input_sha256':None,'inspection_status':'PDF, source image and reflow output not opened'})
 result={'eligibility_amendment':'Before any registry or PDF/image inspection: val manuals, redbooks and chinese_laws each have only one source document and all were seen previously, so unseen-source alternatives FAA regulations, EU tenders and German laws were selected. The declared source-disjoint requirement was not relaxed.','status':'REGISTERED_NOT_EVALUATED','seed':seed,'quotas':quotas,'metadata_only':True,'rule':'Minimum seeded SHA256(filename) per collection, >=2 Text annotations, paper >=1 Formula, PDF <=2 MiB, globally distinct previously-unseen doc_name; no quality-based replacement.','excluded_previous_documents':len(set().union(*(set(nested_docs(json.loads((prior/s['path']).read_text()))) for s in sources))),'exclusion_sources':sources,'excluded_arxiv_ids':sorted(paper_ids),'metadata_sha256':hashlib.sha256(packed).hexdigest(),'expanded_metadata_sha256':hashlib.sha256(raw).hexdigest(),'extra_directory_sha256':hashlib.sha256((metadata/'extra-entries.json').read_bytes()).hexdigest(),'pages':pages,'limitations':['Page/style strata only; not evidence of absent upstream training overlap or semantic near-duplicates.','No adjacent-page continuation claim can be made from this single-page registry.','Actual input SHA256 remains pending; freeze bytes before first source/output inspection.','Hard representation gates currently fail on the original fraction control; these holdouts must remain unopened until a later explicitly versioned candidate is frozen.']}
 output.write_text(json.dumps(result,indent=2));print(json.dumps({'registered':len(pages),'collections':quotas,'previous_documents_excluded':result['excluded_previous_documents'],'status':result['status']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('metadata');p.add_argument('prior');p.add_argument('output');a=p.parse_args();register(a.metadata,a.prior,a.output)
