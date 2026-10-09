"""Lossless content-addressed HTML storage; engine output is reconstructed exactly."""
import pathlib,re,base64,hashlib,json,sys
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';pair=int(sys.argv[1]);root=B/'evidence'/f'D{pair}-assets';root.mkdir(parents=True,exist_ok=True);rows=[]
for p in (B/'output').glob(f'D{pair}-P*-*/*.html'):
 raw=p.read_text()
 if 'asset://' in raw:raise RuntimeError('Already compacted')
 def compact(m):
  data=base64.b64decode(m.group(1));h=hashlib.sha256(data).hexdigest();f=root/(h+'.png')
  if not f.exists():f.write_bytes(data)
  return 'asset://'+h+'.png'
 text=re.sub(r'data:image/png;base64,([A-Za-z0-9+/=]+)',compact,raw);restored=re.sub(r'asset://([a-f0-9]+)\.png',lambda m:'data:image/png;base64,'+base64.b64encode((root/(m.group(1)+'.png')).read_bytes()).decode(),text);assert restored==raw
 p.write_text(text);rows.append({'path':str(p.relative_to(B)),'original_sha256':hashlib.sha256(raw.encode()).hexdigest(),'original_bytes':len(raw.encode()),'stored_bytes':len(text.encode()),'byte_exact_roundtrip':True})
(W/'readest-recovery'/f'PAIR-{pair}-STORAGE.json').write_text(json.dumps(rows,indent=2));print(len(rows),sum(r['original_bytes']-r['stored_bytes'] for r in rows))
