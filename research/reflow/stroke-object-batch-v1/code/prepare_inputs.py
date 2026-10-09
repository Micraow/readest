import pathlib,json,subprocess,hashlib,datetime,fitz,shutil
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent;registry=json.loads((B/'PIPELINE-FREEZE.json').read_text());attempts=[];ready=[]
for s in registry['inputs']:
 path=B/'inputs'/(s['key']+'.pdf')
 if s['partition']=='mechanism_regression':
  for suffix in ['.pdf','.png','-rawdict.json']:
   dst=B/'inputs'/(s['key']+suffix)
   if not dst.exists():dst.symlink_to((W/'native-primitives-v1/inputs'/(s['key']+suffix)).resolve())
  shutil.copyfile(W/'native-primitives-v1/output'/(s['key']+'-detector.json'),B/'output'/(s['key']+'-detector.json'))
 elif not path.exists():
  a={'key':s['key'],'url':s['url'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};attempts.append(a);(B/'DOWNLOAD-ATTEMPTS.json').write_text(json.dumps(attempts,indent=2));r=subprocess.run(['curl','--fail','--location','--max-time','60','--output',str(path),s['url']],capture_output=True,text=True);a.update({'returncode':r.returncode,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});(B/'DOWNLOAD-ATTEMPTS.json').write_text(json.dumps(attempts,indent=2))
  if r.returncode:print('download failed',s['key'],r.stderr,flush=True);raise SystemExit(r.returncode)
 d=fitz.open(path);s.update({'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'pages':len(d),'title':d.metadata.get('title','')});page=d[s['page_1based']-1]
 if s['partition']=='new_source_batch':
  page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False).save(str(B/'inputs'/(s['key']+'.png')));page.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(str(B/'evidence'/(s['key']+'-reference.png')));(B/'inputs'/(s['key']+'-rawdict.json')).write_text(json.dumps(page.get_text('rawdict'),default=lambda v:{'binary_length':len(v)} if isinstance(v,bytes) else str(v)))
 ready.append(s);(B/'INPUT-FREEZE.json').write_text(json.dumps({'inputs':ready},indent=2));print(s,flush=True)
