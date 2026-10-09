"""Acquire only the exact two registered page entries, with a new private ledger."""
import argparse,hashlib,json,pathlib,struct,time,urllib.request,zlib
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
registry=json.loads((root/'readest-research-checkpoint/research/reflow/generic-reflow-v2/HOLDOUT-REGISTRY.json').read_text());entries=json.loads((root/'doclaynet-role-pilot-v1/metadata/extra-entries.json').read_text());pin=next(x for x in json.loads((root/'doclaynet-role-pilot-v1/RANGE-PROBES.json').read_text()) if x['name']=='extra');total=int(pin['content_range'].split('/')[-1]);rows=[]
for key in ['H5','H6']:
 rec=next(x for x in registry['pages'] if x['key']==key);entry='PDF/'+rec['file_name'].removesuffix('.png')+'.pdf';info=entries[entry]
 assert info['expanded']==rec['archive_pdf_expanded_bytes'] and info['crc32']==rec['archive_pdf_crc32'] and info['method']==8
 length=info['compressed']+65566;start=info['offset'];assert length<2*1024**2 and info['expanded']<2*1024**2
 row={'sample':key,'entry':entry,'started_epoch':time.time(),'requested_bytes':length,'status':'requesting','content_inspected':False};rows.append(row);(out/'acquisition.json').write_text(json.dumps(rows,indent=2))
 req=urllib.request.Request(pin['url'],headers={'Range':f'bytes={start}-{start+length-1}','If-Match':pin['etag'],'Accept-Encoding':'identity'})
 with urllib.request.urlopen(req,timeout=60) as response:
  if response.status!=206 or response.headers.get('ETag')!=pin['etag'] or response.headers.get('Content-Range')!=f'bytes {start}-{start+length-1}/{total}':raise RuntimeError('ACQUISITION: range/ETag mismatch')
  raw=response.read(length+1)
 if len(raw)!=length:raise RuntimeError('ACQUISITION: byte count mismatch')
 head=struct.unpack_from('<4s5H3L2H',raw)
 if head[0]!=b'PK\x03\x04' or raw[30:30+head[-2]].decode()!=entry:raise RuntimeError('ACQUISITION: entry mismatch')
 offset=30+head[-2]+head[-1];data=zlib.decompress(raw[offset:offset+info['compressed']],-15)
 if len(data)!=info['expanded'] or zlib.crc32(data)!=info['crc32']:raise RuntimeError('ACQUISITION: CRC/expanded length mismatch')
 (out/(key+'.pdf')).write_bytes(data);row.update(status='acquired_not_parsed',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),range_sha256=hashlib.sha256(raw).hexdigest(),transfer_wall_seconds=time.time()-row['started_epoch'],etag=pin['etag']);(out/'acquisition.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
