"""Explicit seen-data continuation from an independently verified local plan.

No model inference; does not establish a cold-request or blind-holdout pass.
Run with an external wall-time bound such as `timeout 60s`.
"""
import argparse,importlib.util,sys,pathlib,json,time,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('plan');p.add_argument('order');p.add_argument('cached_model');p.add_argument('out');a=p.parse_args()
root=pathlib.Path(a.root).resolve();R=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(a.out).resolve();out.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('candidate',R/'generic-reflow-v2-integrated-paper-1/code/page_pipeline.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
plan=out/'native/fractions';order=out/'native/order';shutil.copytree(a.plan,plan);shutil.copytree(a.order,order)
verified=json.loads((plan/'masked-native-replay.json').read_text());assert verified['ownership_and_replay_pass'];assert json.loads((order/'order-tree-private.json').read_text())['order_tree_built']
rows=[]
def action(name,fn):
 t=time.perf_counter()
 try:r=fn();rows.append(dict(name=name,status='complete',wall_seconds=time.perf_counter()-t));return r
 except Exception as e:rows.append(dict(name=name,status='failed',wall_seconds=time.perf_counter()-t,error=str(e)));raise
 finally:(out/'stages.json').write_text(json.dumps(rows,indent=2))
def stage(name,command):
 def execute():
  with (out/(name+'.stdout')).open('w') as stdout,(out/(name+'.stderr')).open('w') as stderr:subprocess.run([str(x) for x in command],stdout=stdout,stderr=stderr,check=True)
 return action(name,execute)
def gate(ok,kind):
 if not ok:raise RuntimeError(kind)
pdf=pathlib.Path(a.pdf).resolve();model=pathlib.Path(a.cached_model).resolve();cost=json.loads((model/'model-costs.json').read_text())
assets=action('verified_native_assets_reused',lambda:json.loads((plan/'native-unit-assets-private.json').read_text()));gate(not assets['unsupported_source_support_units'],'SUPPORT')
reader=action('tree_reader',lambda:m.build(plan,order));gate(reader['source_unit_bijection'],'BIJECTION')
action('flow_relations',lambda:m.legacy.flow.diagnose(plan,order,model/'prediction-private.json',cost['native_model_input_size'],out/'native/flow'))
reader=action('flow_reader',lambda:m.legacy.flow.build(plan,order,out/'native/flow/flow-relations-private.json'));gate(reader['source_unit_bijection'],'FLOW_BIJECTION')
P=R/'generic-reflow-v2-paragraph-vector/code';runtime=root/'generic-reflow-v2-glyph-resources-local/runtime';python=root/'layout-evaluation/venv/bin/python';capture=out/'capture'
stage('glyph_capture',["node",R/'generic-reflow-v2-glyph-resources/code/probe_stateful.mjs',runtime,a.pdf,capture])
capture_result=json.loads((capture/'result.json').read_text());gate(capture_result['observerDifference']['pixels']==0,'OBSERVER')
bridge=out/'bridge-private.json';stage('native_bridge',[python,R/'generic-reflow-v2-indexed-bridge/code/bridge.py',plan/'plan-private.json',capture/'events-private.json',bridge])
stage('prepare_reader',[python,P/'prepare_reader.py',plan,capture,bridge,out/'prepared'])
stage('target_local_images',[python,P/'request_local_images.py',a.pdf,plan,out/'prepared/fallback-requests-private.json',out/'local-images'])
gate(json.loads((out/'local-images/local-images-private.json').read_text())['all_accepted'],'TARGET_GRID')
stage('update_local_images',[python,P/'update_local_images.py',out/'prepared/reader-data-private.json',out/'local-images/local-images-private.json',out/'updated/reader-data-private.json'])
stage('vector_components',[python,P/'refine_vector_components.py',out/'updated/reader-data-private.json',plan/'plan-private.json',plan/'tree-reader-assets-private.json',bridge,out/'components/reader-data-private.json'])
data=out/'flow-final/reader-data-private.json';stage('flow_refinements',[python,P/'flow_refinements.py',out/'components/reader-data-private.json',plan/'plan-private.json',data,'--events',capture/'events-private.json','--bridge',bridge])
stage('formula_hierarchy',[python,R/'generic-reflow-v2-formula-hierarchy/code/build_hierarchy.py',data,plan/'plan-private.json',out/'native/order/order-tree-private.json',plan/'native-unit-assets-private.json',out/'local-images/local-images-private.json',out/'final'])
data=out/'final/reader-data-private.json'
stage('initial_render_28_dpr2',['node',R/'generic-reflow-v2-formula-hierarchy/code/render_reader.mjs',runtime,data,out/'reader-28','28','2'])
stage('research_html',[python,R/'generic-reflow-v2-integrated-paper-1/code/make_preview.py',data,out/'research-preview-private.html'])
(out/'seen-result.json').write_text(json.dumps(dict(scope='seen cached-plan reader continuation',model_inferences=0,cold_request=False,source_replay_exact=True,reader_generated=True,browser_verified=False,reading_acceptance=False),indent=2))
