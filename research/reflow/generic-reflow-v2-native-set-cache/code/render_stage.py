"""Fresh measured stage, with existing native plan explicitly reused."""
import argparse,json,pathlib,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'generic-reflow-v2-native-components/code'))
from backend_loader import load_backend
load_backend()
from safe_wire import install
from render_cached import render_units,original
p=argparse.ArgumentParser();p.add_argument('mode',choices=['old','new']);p.add_argument('pdf');p.add_argument('source');p.add_argument('out');a=p.parse_args();source=pathlib.Path(a.source);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
for name in ['plan-private.json','ownership-summary.json']:shutil.copyfile(source/name,out/name)
# Resolve existing mask paths; no source PNG asset is copied into the output.
plan=json.loads((out/'plan-private.json').read_text())
for patches in plan['patches'].values():
 for patch in patches:patch['file']=str((source/patch['file']).resolve())
(out/'plan-private.json').write_text(json.dumps(plan,ensure_ascii=False,separators=(',',':')));install(ROOT);r=(original if a.mode=='old' else render_units)(a.pdf,out);print(json.dumps({k:v for k,v in r.items() if k!='results'}))
