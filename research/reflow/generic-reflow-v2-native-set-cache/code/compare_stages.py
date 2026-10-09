import argparse,json,pathlib,subprocess,sys
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('plan');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False);py=root/'layout-evaluation/venv/bin/python';R=root/'readest-research-checkpoint/research/reflow';measure=R/'generic-reflow-v2-localgeometry/code/measure_request.py';script=pathlib.Path(__file__).with_name('render_stage.py');runs=[];reference=None
for index,mode in enumerate(['old','new','new','old']):
 folder=out/(str(index)+'-'+mode);cost=out/(str(index)+'-'+mode+'-cost');subprocess.run([str(x) for x in [py,measure,'--wall-limit','60',cost,py,script,mode,pathlib.Path(a.pdf).resolve(),pathlib.Path(a.plan).resolve(),folder]],check=True,stdout=subprocess.DEVNULL);r=json.loads((folder/'native-unit-assets-private.json').read_text());assets={x['id']:x for x in r['results']};row={'ordinal':index,'mode':mode,'cost':json.loads((cost/'measurement.json').read_text()),'native_renders':r['native_renders'],'cache':r.get('set_cache'),'units':len(assets),'failed_source_support_units':len(r['unsupported_source_support_units'])};diffs=[]
 if reference is None:reference=(folder,assets)
 else:
  refdir,refs=reference
  if assets.keys()!=refs.keys():raise RuntimeError('asset ID set changed')
  for uid,asset in assets.items():
   old=refs[uid];keys=['empty','asset_pixel_box','width_em','height_em','descent_em','source_glyph_records','background','source_interval','mapped_unicode','all_unicode_known'];metrics=[k for k in keys if asset.get(k)!=old.get(k)];record={'unit':uid,'different_metrics':metrics}
   if not asset.get('empty'):
    x=np.array(Image.open(folder/asset['file']));y=np.array(Image.open(refdir/old['file']));shape=x.shape==y.shape;record['shape_equal']=shape
    if shape:
     support=(x[:,:,3]>0)|(y[:,:,3]>0);record.update(alpha_different_pixels=int(np.count_nonzero(x[:,:,3]!=y[:,:,3])),supported_rgba_different_pixels=int(np.count_nonzero(np.any(x[support]!=y[support],axis=1))),all_rgba_different_pixels=int(np.count_nonzero(np.any(x!=y,axis=2))))
   diffs.append(record)
  row['metrics_exact']=all(not x['different_metrics'] for x in diffs);row['alpha_and_supported_rgba_exact']=all(x.get('shape_equal',True) and x.get('alpha_different_pixels',0)==0 and x.get('supported_rgba_different_pixels',0)==0 for x in diffs);row['zero_alpha_only_rgb_different_pixels']=sum(x.get('all_rgba_different_pixels',0) for x in diffs);(folder/'comparison-private.json').write_text(json.dumps(diffs,indent=2))
 runs.append(row);(out/'result.json').write_text(json.dumps({'runs':runs,'cached_source_plan':True,'whole_page_cost':False},indent=2));print(json.dumps({k:v for k,v in row.items() if k not in ['cost']}|{'wall_seconds':row['cost']['wall_seconds'],'total_cpu_seconds':row['cost']['total_accounted_cpu_seconds']}),flush=True)
