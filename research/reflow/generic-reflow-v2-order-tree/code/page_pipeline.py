"""Fresh page path with optional cached/live weak layout prior, no annotation work."""
import argparse,json,pathlib,sys,time,subprocess,resource
P=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'generic-reflow-v2-inkownership/code'));sys.path.insert(0,str(P/'generic-reflow-v2-paintclosure/code'))
from ink_ownership import extract_partitioned_layers
from coalesce_local_intervals import coalesce
from close_paint_units import close_graphics
from close_support_intervals import close as close_support
from render_native_batches import render_units
from masked_native_replay import run as replay
# Restore this isolated layer before importing names which also exist historically.
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from apply_region_priors import apply
from close_native_fractions import close as close_fractions
from diagnose_native_regions import diagnose
from build_tree_reader import build

def run(pdf,out,model_dir=None,cached_detector=None,image_size=None):
    pdf=pathlib.Path(pdf);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);phases=[];start=time.perf_counter()
    def phase(name,fn):
        t=time.perf_counter();r=fn();phases.append(dict(name=name,wall_seconds=time.perf_counter()-t));(out/'phase-costs.json').write_text(json.dumps(phases,indent=2));return r
    if model_dir:
        def isolated_model():
            dest=out/'model';dest.mkdir(exist_ok=True)
            with (dest/'stdout.log').open('w') as stdout,(dest/'stderr.log').open('w') as stderr:
                subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('predict_local_regions.py')),str(pdf),str(dest),str(model_dir)],check=True,stdout=stdout,stderr=stderr)
            return json.loads((dest/'model-costs.json').read_text())
        model=phase('isolated_cold_model_process_import_load_raster_inference',isolated_model);detector=out/'model/prediction-private.json';image_size=model['native_model_input_size']
    else:model=None;detector=cached_detector
    source=out/'native';ownership=phase('native_inventory_stable_ownership',lambda:extract_partitioned_layers(pdf,source))
    if not ownership['all_object_pixels_uniquely_assigned']:phase('within_object_interval_closure',lambda:coalesce(source));source=source/'coalesced'
    phase('graphic_printed_paint_and_text_closure',lambda:close_graphics(source,out/'graphics'));source=out/'graphics'
    phase('cross_object_support_closure',lambda:close_support(source,out/'support'));source=out/'support'
    if detector:phase('verified_weak_region_priors',lambda:apply(source,detector,image_size,out/'priors',origin='live_local_page' if model else 'historical_cache'));source=out/'priors'
    phase('native_fraction_structure',lambda:close_fractions(source,out/'fractions'));source=out/'fractions'
    composition=phase('original_position_native_ownership_replay',lambda:replay(pdf,source))
    order=phase('region_column_line_tree',lambda:diagnose(source,out/'order'))
    if not order['order_tree_built']:raise RuntimeError('region order unresolved; no successful reader generated')
    assets=phase('native_local_batch_render_encode',lambda:render_units(pdf,source));reader=phase('paragraph_inline_bundle_reader',lambda:build(source,out/'order'))
    result=dict(scope='paper-priority printed content; ink annotations excluded by user scope amendment',model_mode='live cold offline PP-S' if model else ('historical cached PP-S' if detector else 'no model'),phases=phases,native_initial_renders=ownership['native_renders'],native_final_replay_renders=composition['native_renders'],native_unit_renders=assets['native_renders'],source_replay_exact=composition['ownership_and_replay_pass'],source_support_failed_units=len(assets['unsupported_source_support_units']),source_unit_bijection=reader['source_unit_bijection'],native_units=reader['emitted_native_units'],paragraphs=reader['paragraphs'],protected_blocks=reader['objects'],reading_tree_leaves=order['leaf_count'],native_index_boundary_conflicts=len(order['native_index_boundary_conflicts']),output_folder=str(source),elapsed_before_final_write=time.perf_counter()-start,parent_process_cpu_seconds=time.process_time(),waited_children_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,reading_acceptance=False,browser_tested=False,holdouts_opened=0)
    (out/'pipeline-result.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');p.add_argument('--model-dir');p.add_argument('--cached-detector');p.add_argument('--image-width',type=int);p.add_argument('--image-height',type=int);a=p.parse_args();print(json.dumps(run(a.pdf,a.out,a.model_dir,a.cached_detector,(a.image_width,a.image_height))))
