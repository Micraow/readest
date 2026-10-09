"""Bounded, ETag-pinned range reader for official ZIP subsets; no mirror fallback."""
import pathlib,json,urllib.request,struct,hashlib,zlib,time,os,resource
B=pathlib.Path(__file__).resolve().parents[1];LIMIT=256*1024**2
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
def get_range(name,start,length,record=True):
 p=next(x for x in json.loads((B/'RANGE-PROBES.json').read_text()) if x['name']==name);total=int(p['content_range'].split('/')[-1]);length=min(length,total-start)
 ledger=B/'RANGE-TRANSFERS.json';rows=json.loads(ledger.read_text()) if ledger.exists() else []
 if sum(x.get('bytes',0) for x in rows)+length>LIMIT or length>80*1024**2:raise RuntimeError('Transfer budget would be exceeded')
 row={'archive':name,'start':start,'requested_bytes':length,'started_epoch':time.time()};rows.append(row);ledger.write_text(json.dumps(rows,indent=2))
 req=urllib.request.Request(p['url'],headers={'Range':f'bytes={start}-{start+length-1}','If-Match':p['etag'],'Accept-Encoding':'identity'})
 with urllib.request.urlopen(req,timeout=60) as r:
  if r.status!=206 or r.headers.get('ETag')!=p['etag'] or r.headers.get('Content-Range')!=f'bytes {start}-{start+length-1}/{total}':raise RuntimeError('Range/ETag mismatch; stop without alternate source')
  out=r.read(length+1)
  if len(out)!=length:raise RuntimeError('Wrong range byte count')
 row.update(bytes=len(out),sha256=hashlib.sha256(out).hexdigest(),seconds=time.time()-row['started_epoch']);ledger.write_text(json.dumps(rows,indent=2));return out

def directory(name):
 tail=(B/'metadata'/(name+'-tail.bin')).read_bytes();z=tail.rfind(b'PK\x06\x06');v=struct.unpack_from('<4sQ2H2L4Q',tail,z);size,offset=v[-2:];path=B/'metadata'/(name+'-central.bin')
 if path.exists():data=path.read_bytes()
 else:data=get_range(name,offset,size);path.write_bytes(data)
 result={};i=0
 while i<len(data):
  h=struct.unpack_from('<4s6H3L5H2L',data,i)
  if h[0]!=b'PK\x01\x02':raise RuntimeError('Unexpected directory signature')
  fn,ex,co=h[10:13];filename=data[i+46:i+46+fn].decode('utf8');extra=data[i+46+fn:i+46+fn+ex];compressed,expanded,local=h[8],h[9],h[-1];q=0
  while q+4<=len(extra):
   typ,n=struct.unpack_from('<HH',extra,q);value=extra[q+4:q+4+n];q+=4+n
   if typ==1:
    nums=iter(struct.unpack('<'+'Q'*(len(value)//8),value[:len(value)//8*8]))
    if expanded==0xffffffff:expanded=next(nums)
    if compressed==0xffffffff:compressed=next(nums)
    if local==0xffffffff:local=next(nums)
  result[filename]={'method':h[4],'crc32':h[7],'compressed':compressed,'expanded':expanded,'offset':local};i+=46+fn+ex+co
 return result

def extract(name,entry,info,dest,max_expanded=256*1024**2):
 dest=pathlib.Path(dest)
 if dest.exists():raise RuntimeError('Refuse to overwrite existing subset artifact')
 if info['expanded']>max_expanded:raise RuntimeError('Uncompressed entry exceeds frozen bound')
 raw=get_range(name,info['offset'],info['compressed']+65566);head=struct.unpack_from('<4s5H3L2H',raw)
 if head[0]!=b'PK\x03\x04':raise RuntimeError('Bad local ZIP header')
 filename=raw[30:30+head[-2]].decode('utf8')
 if filename!=entry:raise RuntimeError('ZIP entry name mismatch')
 offset=30+head[-2]+head[-1];comp=raw[offset:offset+info['compressed']];out=zlib.decompress(comp,-15) if info['method']==8 else comp
 if len(out)!=info['expanded'] or zlib.crc32(out)!=info['crc32']:raise RuntimeError('ZIP CRC/size mismatch')
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out);return {'entry':entry,'bytes':len(out),'sha256':hashlib.sha256(out).hexdigest()}
if __name__=='__main__':
 allmeta={}
 for name in ['core','extra']:
  d=directory(name);(B/'metadata'/(name+'-entries.json')).write_text(json.dumps(d,separators=(',',':')));small={k:v for k,v in d.items() if k.endswith('.json') and ('COCO' in k or k.count('/')<=1)}
  summary={'entries':len(d),'annotation_entries':small if name=='core' else None,'largest_entry_bytes':max(x['expanded'] for x in d.values())};allmeta[name]=summary;print(name,json.dumps(summary)[:4000],flush=True)
 (B/'DIRECTORY-RESULT.json').write_text(json.dumps(allmeta,indent=2))
