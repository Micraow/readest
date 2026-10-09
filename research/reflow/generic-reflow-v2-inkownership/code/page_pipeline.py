"""Single-page research pipeline; every generation/verification phase is timed.

Source bytes must already be local. This is not browser load/interaction timing.
No disk cache from a previous page run is read. Native page resources are opened
and released per phase; their repeated work is included rather than hidden.
"""
import argparse,json,pathlib,time
from ink_ownership import extract_partitioned_layers
from coalesce_local_intervals import coalesce
from masked_native_replay import run as replay
from render_native_units import render_units
from build_unit_reader import build
from annotations import diagnose

def run(pdf,out):
    pdf=pathlib.Path(pdf);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();phases=[]
    def phase(name,fn):
        t=time.perf_counter();r=fn();phases.append(dict(name=name,wall_seconds=time.perf_counter()-t));return r
    ownership=phase('extract_plan_partition_encode',lambda:extract_partitioned_layers(pdf,out))
    groups=None;folder=out
    if not ownership['all_object_pixels_uniquely_assigned']:
        groups=phase('coalesce_repartition_encode',lambda:coalesce(out));folder=out/'coalesced'
    composition=phase('native_masked_source_replay',lambda:replay(pdf,folder))
    annotation=phase('annotation_appearance_and_interaction_inventory',lambda:diagnose(pdf,out/'annotations',key='local diagnostic',scales=(1.,2.)))
    assets=phase('local_native_unit_render_encode',lambda:render_units(pdf,folder))
    reader=phase('build_reflow_reader',lambda:build(folder))
    result=dict(phases=phases,output_folder=str(folder),assets=assets['units'],native_renders=ownership['native_renders']+composition['native_renders']+annotation['render_count']+assets['native_renders'],source_replay_pass=composition['ownership_and_replay_pass'],source_support_mismatched_units=assets['unsupported_source_support_units'],unresolved_pixels=(groups or ownership).get('ambiguous_ink_pixels',0)+(groups or ownership).get('unassigned_ink_pixels',0),all_crops_stable=ownership['all_crops_stable'],annotation_ink_pass_at_tested_scales=all(s['accepted_at_tested_raster_only'] for s in annotation['scales']),annotation_interaction_supported=False,reader_units=reader['emitted_units'],elapsed_before_final_report_seconds=time.perf_counter()-start,holdout_used=False,reading_acceptance=False)
    (out/'pipeline-result.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');a=p.parse_args();print(json.dumps(run(a.pdf,a.out)))
