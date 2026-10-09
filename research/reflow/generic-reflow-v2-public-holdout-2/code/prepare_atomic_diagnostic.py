"""Explicit seen-only local native-region grouping; default cold policy unchanged."""
import argparse,pathlib,json,sys,shutil,hashlib,importlib.util,time
p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('native');p.add_argument('out');p.add_argument('--image-priors',action='store_true');a=p.parse_args();R=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'generic-reflow-v2-localgeometry/code'))
from atomic_native_regions import build,native_interval_conflicts,verify_native_graphic_support
native=pathlib.Path(a.native).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(exist_ok=False);pdf=pathlib.Path(a.pdf).resolve();plan=json.loads((native/'fractions/plan-private.json').read_text());summary=json.loads((native/'fractions/ownership-summary.json').read_text());source=json.loads((native/'fractions/masked-native-replay.json').read_text());old=json.loads((native/'order/order-tree-private.json').read_text());leaves=json.loads((native/'order/source-leaves-private.json').read_text());start=time.perf_counter()
if hashlib.sha256(pdf.read_bytes()).hexdigest()!=summary['input_sha256'] or not source['ownership_and_replay_pass']:raise RuntimeError('exact verified source replay required')
priors=[]
if a.image_priors:
 pred=json.loads((native/'model/prediction-private.json').read_text());size=json.loads((native/'model/model-costs.json').read_text())['native_model_input_size'];W,H=plan['page_size']
 priors=[dict(label=v['label'],score=v['score'],box=[v['coordinate'][0]*W/size[0],v['coordinate'][1]*H/size[1],v['coordinate'][2]*W/size[0],v['coordinate'][3]*H/size[1]]) for v in pred['res']['boxes']]
tree,new,decisions=build(leaves,plan['page_size'],summary['body_font'],image_priors=priors);report=dict(scope='seen native-region diagnostic; not a new holdout or cold request',model_inferences=0,source_replay_exact=True,order_built=tree is not None,decisions=decisions,reader_generated=False,reading_acceptance=False,browser_verified=False)
(out/'grouping-result-private.json').write_text(json.dumps(report,indent=2))
if tree is None:raise RuntimeError('atomic native region evidence insufficient; source PDF fallback remains')
conflicts=native_interval_conflicts(tree['sequence'],new)
if conflicts or old['line_diagnostics']['unresolved_small_units']:raise RuntimeError('native interval or unresolved inline content remains; source PDF fallback')
order=out/'order';order.mkdir();(order/'source-leaves-private.json').write_text(json.dumps(new,indent=2));(order/'order-tree-private.json').write_text(json.dumps(dict(tree,order_tree_built=True,line_diagnostics=old['line_diagnostics'],native_index_boundary_conflicts=[],leaf_count=len(new),reading_acceptance=False,scope='opt-in seen atomic regions; enclosed text not semantically reordered'),indent=2))
folder=out/'plan';shutil.copytree(native/'fractions',folder)
sp=importlib.util.spec_from_file_location('atomic_candidate',R/'generic-reflow-v2-integrated-paper-1/code/page_pipeline.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m);assets=m.render_units(pdf,folder)
support_gates=verify_native_graphic_support(new,plan,assets,folder)
report.update(native_graphic_support=support_gates,seconds=time.perf_counter()-start,unsupported_source_units=len(assets['unsupported_source_support_units']),source_plan_unchanged=(folder/'plan-private.json').read_bytes()==(native/'fractions/plan-private.json').read_bytes(),source_leaf_bijection=tree['original_leaf_bijection'],source_unit_bijection=tree['source_unit_bijection'],native_character_bijection=tree['native_character_bijection'],native_interval_conflicts=0,atomic_regions=sum('source_leaf_ids' in v for v in new))
(out/'native-result-private.json').write_text(json.dumps(report,indent=2))
if assets['unsupported_source_support_units'] or not all(g['accepted'] for g in support_gates):raise RuntimeError('independent native source-support failure; no reading output allowed')
(out/'verified-plan.json').write_text(json.dumps(dict(plan=str(folder),order=str(order),model_inferences=0,cold_request=False,reader_generated=False,browser_verified=False),indent=2));print(json.dumps({k:v for k,v in report.items() if k!='decisions'}))
