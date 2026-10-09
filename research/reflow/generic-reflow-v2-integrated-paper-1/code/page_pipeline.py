"""Compose previously tested isolated mechanisms, retaining old modules unchanged."""
import argparse,importlib.util,json,pathlib,sys,time,subprocess,resource
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
legacy=load('integrated_localgeometry',ROOT/'generic-reflow-v2-localgeometry/code/page_pipeline.py')
for name in ['extract_partitioned_layers','coalesce','close_graphics','close_support','apply','close_fractions','replay','diagnose','build']:globals()[name]=getattr(legacy.flow.old,name)
render_units=legacy.renderer.render_units
DIRECT=ROOT/'generic-reflow-v2-direct-prior/code/direct_prior.py'
sys.path.insert(0,str(ROOT/'generic-reflow-v2-baseline-evidence/code'));from baseline_evidence import run as baseline_run
import paragraph_evidence as pe
for builder in [legacy.tree_reader,legacy.flow_reader]:builder.annotate=pe.annotate;builder.estimate=pe.estimate;builder.can_join=pe.can_join
def run(pdf,out,model_dir=None,cached_detector=None,image_size=None):
    pdf=pathlib.Path(pdf);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);phases=[];start=time.perf_counter()
    def phase(name,fn):
        t=time.perf_counter();r=fn();phases.append(dict(name=name,wall_seconds=time.perf_counter()-t));(out/'phase-costs.json').write_text(json.dumps(phases,indent=2));return r
    if model_dir:
        def isolated_model():
            dest=out/'model'
            with (out/'model.stdout').open('w') as stdout,(out/'model.stderr').open('w') as stderr:
                subprocess.run([sys.executable,str(DIRECT),str(pdf),str(dest),str(model_dir)],check=True,stdout=stdout,stderr=stderr)
            return json.loads((dest/'model-costs.json').read_text())
        model=phase('isolated_cold_model_process_import_load_raster_inference',isolated_model);detector=out/'model/prediction-private.json';image_size=model['native_model_input_size']
    else:model=None;detector=cached_detector
    source=out/'native';ownership=phase('native_inventory_stable_ownership',lambda:extract_partitioned_layers(pdf,source))
    if not ownership['all_object_pixels_uniquely_assigned']:phase('within_object_interval_closure',lambda:coalesce(source));source=source/'coalesced'
    phase('graphic_printed_paint_and_text_closure',lambda:close_graphics(source,out/'graphics'));source=out/'graphics'
    phase('cross_object_support_closure',lambda:close_support(source,out/'support'));source=out/'support'
    if detector:phase('verified_weak_region_priors',lambda:apply(source,detector,image_size,out/'priors',origin='live_local_page' if model else 'historical_cache'));source=out/'priors'
    phase('native_fraction_structure',lambda:close_fractions(source,out/'fractions'));source=out/'fractions'
    baseline=phase('direct_native_baseline_evidence',lambda:baseline_run(source))
    composition=phase('original_position_native_ownership_replay',lambda:replay(pdf,source))
    order=phase('region_column_line_tree',lambda:diagnose(source,out/'order'))
    if not order['order_tree_built']:raise RuntimeError('region order unresolved; no successful reader generated')
    assets=phase('native_local_batch_render_encode',lambda:render_units(pdf,source));reader=phase('paragraph_inline_bundle_reader',lambda:build(source,out/'order'))
    result=dict(scope='paper-priority printed content; ink annotations excluded by user scope amendment',model_mode='live cold offline PP-S' if model else ('historical cached PP-S' if detector else 'no model'),phases=phases,native_initial_renders=ownership['native_renders'],native_final_replay_renders=composition['native_renders'],native_unit_renders=assets['native_renders'],source_replay_exact=composition['ownership_and_replay_pass'],source_support_failed_units=len(assets['unsupported_source_support_units']),source_unit_bijection=reader['source_unit_bijection'],native_units=reader['emitted_native_units'],paragraphs=reader['paragraphs'],protected_blocks=reader['objects'],reading_tree_leaves=order['leaf_count'],native_index_boundary_conflicts=len(order['native_index_boundary_conflicts']),output_folder=str(source),elapsed_before_final_write=time.perf_counter()-start,parent_process_cpu_seconds=time.process_time(),waited_children_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,reading_acceptance=False,browser_tested=False,holdout_accounting='registry external; this candidate diagnoses already seen pages',baseline=baseline)
    (out/'pipeline-result.json').write_text(json.dumps(result,indent=2));return result

legacy.flow.old.run=run
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir',required=True);a=p.parse_args();pe.RETURN_TRACE.clear();r=legacy.flow.run(a.pdf,a.out,a.model_dir,native_renderer=render_units);out=pathlib.Path(a.out);(out/'first-line-return-private.json').write_text(json.dumps(pe.RETURN_TRACE,indent=2));r.update(candidate='integrated-paper-1',blind_acceptance=False);(out/'pipeline-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
