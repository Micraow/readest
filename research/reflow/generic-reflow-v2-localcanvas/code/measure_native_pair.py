"""Paired cold process native-step benchmark, not a complete-page latency."""
import argparse,json,os,pathlib,resource,shutil,subprocess,sys,time

def run(pdf,folder,out):
    folder=pathlib.Path(folder);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);here=pathlib.Path(__file__).resolve().parent;old=here.parents[1]/'generic-reflow-v2-paintclosure/code/render_native_batches.py';new=here/'render_native_localcanvas.py';cpu=min(os.sched_getaffinity(0));results=[]
    for i,variant in enumerate(['original','local_text_guarded','local_text_guarded','original']):
        dst=out/(str(i)+'-'+variant);dst.mkdir(exist_ok=True)
        for f in ['plan-private.json','ownership-summary.json','ownership-records.json']:shutil.copy2(folder/f,dst/f)
        def setup():os.sched_setaffinity(0,{cpu})
        start=time.perf_counter();load_before=os.getloadavg();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (dst/'stdout.txt').open('w') as stdout,(dst/'stderr.txt').open('w') as stderr:
            r=subprocess.run([sys.executable,str(old if variant=='original' else new),str(pdf),str(dst)],stdout=stdout,stderr=stderr,preexec_fn=setup)
        after=resource.getrusage(resource.RUSAGE_CHILDREN);d=json.loads((dst/'native-unit-assets-private.json').read_text()) if r.returncode==0 else None
        results.append(dict(variant=variant,cpu_affinity=[cpu],wall_seconds=time.perf_counter()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,load_before=list(load_before),load_after=list(os.getloadavg()),exit_code=r.returncode,native_step_seconds=d['seconds'] if d else None,source_failed_units=len(d['unsupported_source_support_units']) if d else None))
    first=out/'0-original';comparison=[];ref=json.loads((first/'native-unit-assets-private.json').read_text());mapping={u['id']:u for u in ref['results']}
    for i in [1,2,3]:
        dst=out/(str(i)+'-'+results[i]['variant']);data=json.loads((dst/'native-unit-assets-private.json').read_text());differences=[]
        for u in data['results']:
            v=mapping[u['id']]
            if u.get('empty')!=v.get('empty') or u.get('asset_pixel_box')!=v.get('asset_pixel_box') or (not u.get('empty') and (dst/u['file']).read_bytes()!=(first/v['file']).read_bytes()):differences.append(u['id'])
        comparison.append(dict(run=i,asset_count=len(data['results']),all_asset_bytes_and_coordinates_equal=not differences,differing_units=differences))
    result=dict(scope='existing plan and masks; fresh native-render process only; not page E2E; OS file cache not flushed',schedule='A B B A sequential; shared-machine load recorded, not isolated hardware',runs=results,comparisons=comparison);(out/'pair-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('folder');p.add_argument('out');a=p.parse_args();run(a.pdf,a.folder,a.out)
