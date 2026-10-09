"""Isolated adapters on frozen source/flow pipeline; never rewrite predecessors."""
import argparse,importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];FLOW=ROOT/'generic-reflow-v2-flow-relations/code';sys.path.insert(0,str(FLOW))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
flow=load('localgeometry_frozen_flow',FLOW/'page_pipeline.py')
sys.path.insert(0,str(HERE));from global_alpha import extract
from direction_groups import run as directions
prior=load('localgeometry_prior',HERE/'apply_region_priors.py');order=load('localgeometry_order',HERE/'diagnose_native_regions.py')
renderer=load('localgeometry_localcanvas',ROOT/'generic-reflow-v2-localcanvas/code/render_native_localcanvas.py')
def inventory(pdf,out):
 return extract(pdf,out)
flow.old.extract_partitioned_layers=inventory;flow.old.apply=prior.apply;flow.old.diagnose=order.diagnose
tree_reader=load('localgeometry_tree_reader',HERE/'build_tree_reader.py');flow_reader=load('localgeometry_flow_reader',HERE/'build_flow_reader.py');flow.old.build=tree_reader.build;flow.build=flow_reader.build
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir');p.add_argument('--cached-detector');p.add_argument('--image-width',type=int);p.add_argument('--image-height',type=int);a=p.parse_args();r=flow.run(a.pdf,a.out,a.model_dir,a.cached_detector,(a.image_width,a.image_height),native_renderer=renderer.render_units);r.update(candidate='localgeometry seen-page repair',blind_acceptance=False);(pathlib.Path(a.out)/'pipeline-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
