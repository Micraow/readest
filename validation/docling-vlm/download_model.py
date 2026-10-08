"""Download a fixed official public model release, verifying every file."""
import hashlib,json,urllib.request
from pathlib import Path
base=Path(__file__).resolve().parent
model=json.loads((base/'manifest.json').read_text())['model']
assert model['repo']=='ibm-granite/granite-docling-258M'
assert sum(f['size'] for f in model['files']) < 600*1024**2
root=base/'models'/model['repo'].replace('/','--');root.mkdir(parents=True,exist_ok=True)
verified=[]
for item in model['files']:
 name=item['path'];assert '/' not in name
 url=f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{name}"
 target=root/name;sha256=hashlib.sha256();blob=hashlib.sha1(f"blob {item['size']}\0".encode());total=0
 with urllib.request.urlopen(url,timeout=90) as response,target.open('wb') as output:
  while chunk:=response.read(1024*1024):
   total+=len(chunk)
   if total>item['size']:raise RuntimeError('Oversized model file '+name)
   output.write(chunk);sha256.update(chunk);blob.update(chunk)
 assert total==item['size'],name
 assert (sha256.hexdigest()==item['sha256']) if item['sha256'] else (blob.hexdigest()==item['gitBlobSha1']),name
 verified.append({'path':name,'bytes':total,'sha256':sha256.hexdigest()})
 print(name,total,sha256.hexdigest(),flush=True)
(base/'evidence'/'model-files.json').write_text(json.dumps(verified,indent=2))
