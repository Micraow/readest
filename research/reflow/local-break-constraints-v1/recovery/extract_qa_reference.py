"""Official QA references keyed by(split,image_id); never supplied to inference."""
import pathlib,json,sys,collections,os,hashlib
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});sys.path.insert(0,str(W/'doclaynet-role-pilot-v1/code'));from stream_annotations import iterate
pages=json.loads((B/'INPUT-SELECTION.json').read_text())['pages'];rows={(p['official_split'],p['id']):{'metadata':p,'annotations':[]} for p in pages};cats={}
for split in sorted({p['official_split'] for p in pages}):
 assert (W/'doclaynet-role-pilot-v1/metadata'/(split+'.deflate')).exists()
 for kind,a in iterate(split):
  if kind=='categories':cats[a['id']]=a['name']
  elif kind=='annotations' and (split,a['image_id']) in rows and a.get('precedence',0)==0:rows[(split,a['image_id'])]['annotations'].append(a)
checks=[]
for p in rows.values():
 expected=p['metadata']['class_counts'];got=dict(collections.Counter(str(a['category_id']) for a in p['annotations']));assert expected==got,(p['metadata']['key'],expected,got);checks.append({'key':p['metadata']['key'],'counts_match_frozen_selection':True,'counts':got})
f=B/'QA-REFERENCE.json';old=B/'QA-REFERENCE-before-split-fix.json'
if f.exists() and not old.exists():f.rename(old)
f.write_text(json.dumps({'scope':'QA only; tuple(split,image_id) avoids cross-split ID collision; class counts checked against preselected metadata','categories':cats,'pages':list(rows.values())},indent=2));result={'scope':'Scoring tool correction, engine untouched','bug':'Previous loader keyed onlyimage_id, mixing train annotations into valD3-P2(id2553)','old_official_Text_List_regions':95,'correct_official_Text_List_regions':sum(a['category_id'] in [4,10] for p in rows.values() for a in p['annotations']),'checks':checks,'old_reference_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'corrected_reference_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'original_95_region_mechanical_results':'Invalidated, not a reflow score','visual_scope':'D3-P2 old QA overlay contained wrong region labels; original PDF/output unchanged'};(W/'readest-recovery/QA-SPLIT-CORRECTION.json').write_text(json.dumps(result,indent=2));print(result['correct_official_Text_List_regions'])
