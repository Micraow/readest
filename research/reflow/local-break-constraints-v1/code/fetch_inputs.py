import pathlib,json,sys,time
B=pathlib.Path(__file__).resolve().parents[1];P=B.parent/'doclaynet-role-pilot-v1';sys.path.insert(0,str(P/'code'));from remote_zip import extract
pages=json.loads((B/'INPUT-SELECTION.json').read_text())['pages'];indices={n:json.loads((P/'metadata'/(n+'-entries.json')).read_text()) for n in ['core','extra']};receipt=B/'INPUT-RECEIPTS.json';rows=json.loads(receipt.read_text()) if receipt.exists() else []
for page in pages:
 name=page['file_name'][:-4]
 for archive,entry,suffix in [('extra','PDF/'+name+'.pdf','.pdf'),('core','PNG/'+name+'.png','-official.png')]:
  dest=B/'inputs'/(page['key']+suffix)
  if dest.exists():continue
  r=extract(archive,entry,indices[archive][entry],dest,max_expanded=4*1024**2);rows.append({'key':page['key'],'archive':archive,**r});receipt.write_text(json.dumps(rows,indent=2))
 print(page['key']+' downloaded and verified; not inspected',flush=True)
