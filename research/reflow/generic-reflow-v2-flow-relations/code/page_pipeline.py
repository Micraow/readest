"""Cold original pipeline plus separately timed relation/reader phase."""
import argparse,importlib.util,json,pathlib,resource,sys,time
HERE=pathlib.Path(__file__).resolve().parent;OLD=HERE.parents[1]/'generic-reflow-v2-order-tree/code';sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('checkpoint_order_pipeline',OLD/'page_pipeline.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
sys.path.insert(0,str(HERE))
from diagnose_flow import diagnose
from build_flow_reader import build

def run(pdf,out,model_dir=None,cached_detector=None,image_size=None,native_renderer=None):
    start=time.perf_counter();out=pathlib.Path(out);previous_renderer=old.render_units
    if native_renderer is not None:old.render_units=native_renderer
    try:r=old.run(pdf,out,model_dir,cached_detector,image_size)
    finally:old.render_units=previous_renderer
    folder=pathlib.Path(r['output_folder']);prior=dict(r)
    if model_dir:
        prediction=out/'model/prediction-private.json';image_size=json.loads((out/'model/model-costs.json').read_text())['native_model_input_size']
    else:prediction=cached_detector
    if prediction:
        t=time.perf_counter();flow=diagnose(folder,out/'order',prediction,image_size,out/'flow');r['phases'].append(dict(name='main_flow_and_float_relations',wall_seconds=time.perf_counter()-t));t=time.perf_counter();reader=build(folder,out/'order',out/'flow/flow-relations-private.json');r['phases'].append(dict(name='flow_relation_reader_rebuild',wall_seconds=time.perf_counter()-t));r.update(paragraphs=reader['paragraphs'],flow_relations=len(flow['relations']),source_unit_bijection=reader['source_unit_bijection'],native_index_monotonicity_claimed=False)
    else:r.update(flow_relations=0,flow_relation_scope='no weak caption source; no relocation attempted')
    r.update(elapsed_before_final_write=time.perf_counter()-start,parent_process_cpu_seconds=time.process_time(),waited_children_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime)
    (out/'original-tree-pipeline-result.json').write_text(json.dumps(prior,indent=2));(out/'pipeline-result.json').write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir');p.add_argument('--cached-detector');p.add_argument('--image-width',type=int);p.add_argument('--image-height',type=int);a=p.parse_args();print(json.dumps(run(a.pdf,a.out,a.model_dir,a.cached_detector,(a.image_width,a.image_height))))
