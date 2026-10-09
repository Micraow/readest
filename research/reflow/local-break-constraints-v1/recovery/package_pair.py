import pathlib,json,zipfile,hashlib,sys
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';pair=int(sys.argv[1]);dest=W/'readest-recovery'/f'readest-replay-pair-{pair}-20261009.zip';files=[]
for p in (B/'output').glob(f'D{pair}-P*'):
 if p.is_file():files.append(p)
 else:files += [f for f in p.rglob('*') if f.is_file() and f.suffix in ['.json','.html','.png','.log']]
for p in (B/'evidence').glob(f'D{pair}-*'):
 if p.is_file():files.append(p)
 else:files += [f for f in p.rglob('*') if f.is_file() and f.suffix in ['.json','.png']]
files += [f for f in (W/'readest-recovery').glob(f'PAIR-{pair}-*.json')]+[W/'readest-recovery/compact_pair.py',W/'readest-recovery/snapshot_restored.py',W/'readest-recovery/run_no_font_hint.py',W/'readest-recovery/replay_pair.py',W/'readest-recovery/qa_layout_blit.py']
manifest={'scope':'Private raw evidence checkpoint after reset, same frozen algorithm; no claim of full visual or product acceptance','pair':pair,'base_commit':'9f6b88cfa9b15169f7d739b10c350efa261e19dd','files':{str(p.relative_to(W)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},'html_storage':'asset:// hashes point to pair-local evidence PNGs; rehydrate via snapshot_restored.py or replace placeholders with matching base64 to reconstruct byte-exact HTML'}
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,str(p.relative_to(W)))
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
print(dest.stat().st_size,len(files))
