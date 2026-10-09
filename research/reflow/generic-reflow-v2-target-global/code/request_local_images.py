"""Regenerate declared local fallback groups at the real font/DPR sampling grid."""
import argparse,io,json,pathlib,sys,time,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'generic-reflow-v2-native-components/code'))
from backend_loader import load_backend,bind_asset_identity
backend_report=load_backend()
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-targetgrid/code'))
from asset_service import NativeAssetService
from safe_wire import install,report as wire_report,CompactJSON
bind_asset_identity()
from install import install_global_renderer
if '--old' in sys.argv:sys.argv.remove('--old');global_report={'old_renderer':True}
else:global_report=install_global_renderer()
wire_changes=install(ROOT);json=CompactJSON("target_request_cli")
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('plan');p.add_argument('requests');p.add_argument('out');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);service=NativeAssetService(a.pdf,a.plan,out/'requests');ids=json.loads(pathlib.Path(a.requests).read_text())['units'];reports=[];assets={};start=time.perf_counter();cpu=time.process_time()
for n in range(0,len(ids),8):
 payload,report=service.request(ids[n:n+8],28,2);reports.append(report)
 if payload is None:break
 dest=out/f'batch-{n//8}';dest.mkdir()
 with zipfile.ZipFile(io.BytesIO(payload)) as z:
  data=json.loads(z.read('assets.json'))
  for asset in data['results']:
   if asset.get('empty'):continue
   f=dest/asset['file'];f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(z.read(asset['file']));assets[asset['id']]={**asset,'absolute_file':str(f.resolve()),'grid':report['grid']}
result={'requested_units':len(ids),'accepted_units':len(assets),'all_accepted':set(assets)==set(ids),'reports':reports,'assets':assets,'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'preprocessing_reused':True,'whole_page_cold_cost':False};(out/'local-images-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='assets'}))

(out/"compact-wire-report.json").write_text(json.dumps(wire_report(wire_changes),indent=2))

(out/"component-backend.json").write_text(json.dumps(backend_report|{"scipy_imported_in_target_process":any(n=="scipy" or n.startswith("scipy.") for n in sys.modules)},indent=2))

(out/"global-renderer.json").write_text(json.dumps(global_report,indent=2))
