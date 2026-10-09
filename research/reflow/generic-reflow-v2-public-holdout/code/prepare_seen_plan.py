"""Opt-in cached-model native repair experiment, with all native gates retained.

Run with an external process bound, e.g. timeout 60s. Each stage executes once;
one rendered-support closure is allowed only after a concrete asset mismatch.
"""
import argparse,importlib.util,pathlib,sys,json,time
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('cached_model');p.add_argument('out');a=p.parse_args();R=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(a.out).resolve();out.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('candidate',R/'generic-reflow-v2-integrated-paper-1/code/page_pipeline.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
sys.path.insert(0,str(R/'generic-reflow-v2-localgeometry/code'));from rendered_support import close
pdf=pathlib.Path(a.pdf).resolve();model=pathlib.Path(a.cached_model).resolve();cost=json.loads((model/'model-costs.json').read_text());rows=[]
def stage(name,fn):
 t=time.perf_counter()
 try:r=fn();rows.append(dict(stage=name,seconds=time.perf_counter()-t,status='complete'));return r
 except Exception as e:rows.append(dict(stage=name,seconds=time.perf_counter()-t,status='failed',error=str(e)));raise
 finally:(out/'stages.json').write_text(json.dumps(rows,indent=2))
source=out/'native';ownership=stage('opt_in_native_extract',lambda:m.legacy.extract(pdf,source,experimental_fraction_support=True))
if not ownership['all_object_pixels_uniquely_assigned']:stage('coalesce',lambda:m.coalesce(source));source=source/'coalesced'
stage('graphics',lambda:m.close_graphics(source,out/'graphics'));source=out/'graphics'
stage('support',lambda:m.close_support(source,out/'support'));source=out/'support'
stage('cached_priors',lambda:m.apply(source,model/'prediction-private.json',cost['native_model_input_size'],out/'priors',origin='historical_cache'));source=out/'priors'
stage('fractions',lambda:m.close_fractions(source,out/'fractions'));source=out/'fractions'
def verify(tag):
 stage(tag+'_baseline',lambda:m.baseline_run(source));replay=stage(tag+'_replay',lambda:m.replay(pdf,source));order=stage(tag+'_order',lambda:m.diagnose(source,out/(tag+'-order')))
 if not replay['ownership_and_replay_pass'] or not order['order_tree_built']:raise RuntimeError('replay or order gate failed')
 return stage(tag+'_assets',lambda:m.render_units(pdf,source))
assets=verify('initial');tag='initial'
if assets['unsupported_source_support_units']:
 stage('rendered_support_closure',lambda:close(source,out/'rendered-support'));source=out/'rendered-support';tag='closed';assets=verify(tag)
if assets['unsupported_source_support_units']:raise RuntimeError('independent source support still fails')
(out/'verified-plan.json').write_text(json.dumps(dict(plan=str(source),order=str(out/(tag+'-order')),model_inferences=0,cold_request=False,reader_generated=False,browser_verified=False),indent=2))
