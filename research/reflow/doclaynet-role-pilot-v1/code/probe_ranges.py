import pathlib,json,urllib.request,datetime,hashlib,os,resource
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
B=pathlib.Path(__file__).resolve().parents[1];plan=json.loads((B/'ACCESS-PLAN.json').read_text());rows=[]
for name in ['core','extra']:
 url=plan[name+'_url'];record={'name':name,'url':url,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};rows.append(record)
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=-65536','Accept-Encoding':'identity'}),timeout=30) as r:
   record.update(status=r.status,etag=r.headers.get('ETag'),content_range=r.headers.get('Content-Range'))
   if r.status!=206:raise RuntimeError('Range response was not 206; full archive transfer refused')
   data=r.read(65537)
   if len(data)>65536:raise RuntimeError('Range response exceeded 65536 byte limit')
   record.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest());(B/'metadata'/(name+'-tail.bin')).write_bytes(data)
 except Exception as e:record['error']=type(e).__name__+': '+str(e)
 (B/'RANGE-PROBES.json').write_text(json.dumps(rows,indent=2));print(json.dumps(record),flush=True)
 if 'error' in record:break
