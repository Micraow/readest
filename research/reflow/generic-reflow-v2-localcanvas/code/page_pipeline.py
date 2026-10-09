"""Switchable local-text canvas in complete native+model+flow pipeline."""
import argparse,importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;FLOW=HERE.parents[1]/'generic-reflow-v2-flow-relations/code';sys.path.insert(0,str(FLOW))
spec=importlib.util.spec_from_file_location('flow_pipeline',FLOW/'page_pipeline.py');flow=importlib.util.module_from_spec(spec);spec.loader.exec_module(flow)
sys.path.insert(0,str(HERE))
from render_native_localcanvas import render_units
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir');p.add_argument('--cached-detector');p.add_argument('--image-width',type=int);p.add_argument('--image-height',type=int);a=p.parse_args();r=flow.run(a.pdf,a.out,a.model_dir,a.cached_detector,(a.image_width,a.image_height),native_renderer=render_units);r['native_renderer']='local canvas only for text with independent alpha masks; original full internal canvas for nontext';(pathlib.Path(a.out)/'pipeline-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
