"""Bounded same-source recovery; static tensor data only, never remote code."""
import pathlib,json,urllib.request,hashlib,time,datetime,struct,math
B=pathlib.Path(__file__).resolve().parent;m=json.loads((B/'MODEL-METADATA.json').read_text());url='https://huggingface.co/'+m['repo']+'/resolve/'+m['revision']+'/model.safetensors';path=B/'model/model.safetensors'
if path.exists():raise SystemExit('Inspect existing model; do not download again')
pro={'url':url,'revision':m['revision'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'max_bytes':250000000,'max_seconds':60,'recovery':'Previous process was lost; no weight file or completion record existed.'};(B/'DOWNLOAD-PROVENANCE.json').write_text(json.dumps(pro,indent=2));t=time.monotonic();h=hashlib.sha256();n=0
try:
 with urllib.request.urlopen(url,timeout=30) as response,path.open('wb') as out:
  while True:
   b=response.read(1024*1024)
   if not b:break
   n+=len(b)
   if n>250000000 or time.monotonic()-t>60:raise RuntimeError('Download budget exceeded')
   out.write(b);h.update(b)
 pro.update({'bytes':n,'seconds':time.monotonic()-t,'sha256':h.hexdigest(),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 pointer=B/'MODEL-LFS-POINTER.txt'
 if pointer.exists():
  ls=pointer.read_text().splitlines();expected=next(x.split('sha256:')[1] for x in ls if x.startswith('oid '));size=int(next(x.split()[1] for x in ls if x.startswith('size ')));pro['matches_official_lfs']=expected==h.hexdigest() and size==n
 with path.open('rb') as f:
  header_n=struct.unpack('<Q',f.read(8))[0]
  if header_n>2000000:raise ValueError('Unexpected safetensors header size')
  head=json.loads(f.read(header_n))
 keys=[k for k in head if k.startswith('reading_order.')];pro['reading_order_tensors']=len(keys);pro['reading_order_parameters']=sum(math.prod(head[k]['shape']) for k in keys);pro['reading_order_tensor_bytes']=sum(head[k]['data_offsets'][1]-head[k]['data_offsets'][0] for k in keys)
 (B/'READING-ORDER-TENSOR-METADATA.json').write_text(json.dumps({'header_bytes':header_n,'tensors':{k:head[k] for k in keys}},indent=2))
except Exception as e:pro.update({'bytes_written':n,'error_type':type(e).__name__,'error':str(e),'seconds':time.monotonic()-t});raise
finally:(B/'DOWNLOAD-PROVENANCE.json').write_text(json.dumps(pro,indent=2));print(pro,flush=True)
