"""A-B-B-A local-asset stage; never claims full cold page cost."""
import argparse,json,pathlib,subprocess
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('plan');p.add_argument('requests');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False);py=root/'layout-evaluation/venv/bin/python';R=root/'readest-research-checkpoint/research/reflow';measure=R/'generic-reflow-v2-localgeometry/code/measure_request.py';script=pathlib.Path(__file__).with_name('request_local_images.py');runs=[];reference=None
for i,mode in enumerate(['old','new','new','old']):
 folder=out/f'{i}-{mode}';cost=out/f'{i}-{mode}-cost';cmd=[py,measure,'--wall-limit','60',cost,py,script,pathlib.Path(a.pdf).resolve(),pathlib.Path(a.plan).resolve(),pathlib.Path(a.requests).resolve(),folder]+(['--old'] if mode=='old' else []);subprocess.run([str(x) for x in cmd],check=True,stdout=subprocess.DEVNULL);m=json.loads((cost/'measurement.json').read_text());row={'ordinal':i,'mode':mode,'measurement':m};path=folder/'local-images-private.json'
 if not path.exists():row['failure']='no complete target-asset report'
 else:
  result=json.loads(path.read_text());row.update(all_accepted=result['all_accepted'],requested_units=result['requested_units'],accepted_units=result['accepted_units']);details=[json.loads(p.read_text()) for p in sorted((folder/'requests').glob('*/target-grid-result.json'))];row['mask_native_renders']=sum(x['native_mask_renders'] for x in details);row['asset_native_renders']=sum(x['native_asset_renders'] for x in details);row['global_alpha_bitmaps']=sum(x.get('global_alpha_canvas',{}).get('allocated_bitmaps',0) for x in details) if mode=='new' else None;assets=result['assets'];diffs=[]
  if reference is None:reference=assets
  else:
   row['unit_id_set_equal']=assets.keys()==reference.keys()
   for uid in set(assets)&set(reference):
    new=assets[uid];old=reference[uid];keys=['asset_pixel_box','width_em','height_em','descent_em','source_glyph_records','background','source_interval','mapped_unicode','all_unicode_known','logical_box_pdf','ink_box_pdf','drawing_offset_pdf','logical_size_pdf','grid'];rec={'unit':uid,'different_metrics':[k for k in keys if new.get(k)!=old.get(k)]};x=np.array(Image.open(new['absolute_file']));y=np.array(Image.open(old['absolute_file']));rec['shape_equal']=x.shape==y.shape
    if rec['shape_equal']:
     support=(x[:,:,3]>0)|(y[:,:,3]>0);rec.update(alpha_diff_pixels=int(np.count_nonzero(x[:,:,3]!=y[:,:,3])),supported_rgba_diff_pixels=int(np.count_nonzero(np.any(x[support]!=y[support],axis=1))),zero_alpha_rgb_diff_pixels=int(np.count_nonzero(np.any(x[~support]!=y[~support],axis=1))))
    diffs.append(rec)
   (folder/'comparison-private.json').write_text(json.dumps(diffs,indent=2));row['metrics_exact']=row['unit_id_set_equal'] and all(not x['different_metrics'] for x in diffs);row['alpha_supported_RGBA_exact']=row['unit_id_set_equal'] and all(x['shape_equal'] and x.get('alpha_diff_pixels',0)==x.get('supported_rgba_diff_pixels',0)==0 for x in diffs);row['zero_alpha_RGB_different_pixels']=sum(x.get('zero_alpha_rgb_diff_pixels',0) for x in diffs)
 runs.append(row);(out/'result.json').write_text(json.dumps({'runs':runs,'existing_plan_reused':True,'complete_page_cost':False},indent=2));print(json.dumps({k:v for k,v in row.items() if k!='measurement'}|{'wall_seconds':m['wall_seconds'],'cpu_seconds':m['total_accounted_cpu_seconds']}),flush=True)
 if row.get('failure') or not row.get('all_accepted'):break
