import argparse,json,pathlib
from text_map import build
p=argparse.ArgumentParser();p.add_argument('reader');p.add_argument('plan');p.add_argument('capture');p.add_argument('bridge');p.add_argument('out');a=p.parse_args();args=[json.loads(pathlib.Path(getattr(a,x)).read_text()) for x in ['reader','plan','capture','bridge']];r=build(*args);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);(out/'text-map-private.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));(out/'summary.json').write_text(json.dumps(r['summary'],indent=2));print(json.dumps(r['summary']))
