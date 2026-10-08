"""Bound each page independently, preserving failures and continuing unchanged pages."""
import json,subprocess,sys,time
from pathlib import Path
manifest=json.loads(Path('/study/manifest.json').read_text());out=Path('/output');runs=[]
deadline=json.loads(Path('/study/budget.json').read_text())['computeDeadlineEpoch']
for source in manifest['sources']:
 for page in source['pages']:
  key=f"{source['key']}-p{page:02d}";start=time.monotonic()
  if time.time()+300>deadline:
   runs.append({'key':key,'returncode':125,'seconds':0,'failure':'budget_exhausted_before_page','remainingSeconds':max(0,deadline-time.time())})
   (out/'batch.json').write_text(json.dumps(runs,indent=2));print(json.dumps(runs[-1]),flush=True)
   continue
  try:
   result=subprocess.run([sys.executable,'/study/convert_page.py',source['key'],str(page)],timeout=300)
   entry={'key':key,'returncode':result.returncode,'seconds':time.monotonic()-start}
  except subprocess.TimeoutExpired:
   entry={'key':key,'returncode':124,'seconds':time.monotonic()-start,'failure':'page_timeout_300s'}
  runs.append(entry);(out/'batch.json').write_text(json.dumps(runs,indent=2));print(json.dumps(entry),flush=True)
assert len(runs)==4
raise SystemExit(any(r['returncode'] for r in runs))
