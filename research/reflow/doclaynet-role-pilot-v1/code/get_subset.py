"""Download only the frozen original-license page subset and retain matched labels."""
import pathlib,json,time,hashlib
from remote_zip import B,extract
from stream_annotations import iterate
selection=json.loads((B/'SELECTION-FREEZE.json').read_text())['pages'];man=B/'SUBSET-DOWNLOAD.json';records=json.loads(man.read_text()) if man.exists() else []
indices={n:json.loads((B/'metadata'/(n+'-entries.json')).read_text()) for n in ['core','extra']}
for split in ['train','val','test']:
 target={r['id']:r for r in selection if r['split']==split};annotations={i:[] for i in target}
 for section,row in iterate(split):
  if section=='annotations' and row['image_id'] in target and row.get('precedence',0)==0:annotations[row['image_id']].append(row)
 for i,r in target.items():
  name=r['file_name'][:-4];d=B/'data'/name;d.mkdir(exist_ok=True);(d/'annotations.json').write_text(json.dumps({'image':r,'annotations':annotations[i]},indent=2))
for j,r in enumerate(selection):
 name=r['file_name'][:-4];d=B/'data'/name
 for archive,entry,filename in [('extra','PDF/'+name+'.pdf','source.pdf'),('core','PNG/'+name+'.png','source.png')]:
  dest=d/filename
  if dest.exists():continue
  start=time.monotonic()
  try:
   result=extract(archive,entry,indices[archive][entry],dest,max_expanded=4*1024**2);records.append({'split':r['split'],'page_hash':name,'archive':archive,**result,'seconds':time.monotonic()-start,'status':'verified CRC and SHA256'})
  except Exception as e:
   records.append({'split':r['split'],'page_hash':name,'archive':archive,'entry':entry,'status':'failed','error':type(e).__name__+': '+str(e)});man.write_text(json.dumps(records,indent=2));raise
  man.write_text(json.dumps(records,indent=2))
 print(json.dumps({'completed_page':j+1,'of':len(selection),'split':r['split'],'collection':r['collection']}),flush=True)
