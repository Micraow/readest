"""Post-timeout diagnosis only: reuse individually accepted immutable requests."""
import argparse,hashlib,io,json,pathlib,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-targetgrid/code'))
from asset_service import NativeAssetService
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('plan');p.add_argument('requests');p.add_argument('previous');p.add_argument('out');a=p.parse_args();folder=pathlib.Path(a.plan);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);ids=json.loads(pathlib.Path(a.requests).read_text())['units'];assets={};source=hashlib.sha256(pathlib.Path(a.pdf).read_bytes()).hexdigest();planhash=hashlib.sha256((folder/'plan-private.json').read_bytes()+(folder/'ownership-summary.json').read_bytes()).hexdigest();reused=[];start=time.perf_counter()
for p in sorted(pathlib.Path(a.previous).glob('*/target-grid-result.json')):
 r=json.loads(p.read_text())
 if not r['target_grid_accepted']:continue
 if r['source_sha256']!=source or r['plan_policy_sha256']!=planhash or r['request']['font_css_px']!=28 or r['request']['dpr']!=2:raise RuntimeError('cache identity/target mismatch')
 data=json.loads((p.parent/'native-unit-assets-private.json').read_text())
 for item in data['results']:
  if item.get('empty'):continue
  if item['id'] in assets:raise RuntimeError('duplicate cached native unit')
  assets[item['id']]={**item,'absolute_file':str((p.parent/item['file']).resolve()),'grid':r['grid_selection']['grid']}
 reused.append(str(p.resolve()))
missing=sorted(set(ids)-set(assets));service=NativeAssetService(a.pdf,a.plan,out/'requests');reports=[]
for n in range(0,len(missing),8):
 payload,report=service.request(missing[n:n+8],28,2);reports.append(report)
 if payload is None:raise RuntimeError('remaining target request rejected')
 dest=out/f'batch-{n//8}';dest.mkdir()
 with zipfile.ZipFile(io.BytesIO(payload)) as z:
  for item in json.loads(z.read('assets.json'))['results']:
   if item.get('empty'):continue
   f=dest/item['file'];f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(z.read(item['file']));assets[item['id']]={**item,'absolute_file':str(f.resolve()),'grid':report['grid']}
r={'assets':assets,'all_accepted':set(ids)==set(assets),'requested_units':len(ids),'accepted_units':len(assets),'reused_accepted_request_files':reused,'newly_requested_units':len(missing),'reports':reports,'resume_wall_seconds':time.perf_counter()-start,'whole_cold_page':False,'original_page_budget_failed':True};(out/'local-images-private.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['assets','reused_accepted_request_files']}))
