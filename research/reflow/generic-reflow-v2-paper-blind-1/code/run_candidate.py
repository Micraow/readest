"""Execute the frozen, complete candidate once; no heuristic changes or retries."""
import argparse,json,pathlib,subprocess,time,resource,sys
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('out');a=p.parse_args()
root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
R=root/'readest-research-checkpoint/research/reflow';P=R/'generic-reflow-v2-paragraph-vector/code';runtime=root/'generic-reflow-v2-glyph-resources-local/runtime';python=root/'layout-evaluation/venv/bin/python';plan=out/'native/fractions';capture=out/'capture';rows=[]
def usage():
 r=resource.getrusage(resource.RUSAGE_CHILDREN);return r.ru_utime+r.ru_stime+time.process_time()
def stage(name,command):
 row={'name':name,'status':'running','started_epoch':time.time()};rows.append(row);(out/'stages.json').write_text(json.dumps(rows,indent=2));t=time.perf_counter();c=usage()
 with (out/(name+'.stdout')).open('w') as stdout,(out/(name+'.stderr')).open('w') as stderr:r=subprocess.run([str(x) for x in command],stdout=stdout,stderr=stderr)
 row.update(status='complete' if r.returncode==0 else 'failed',exit_code=r.returncode,wall_seconds=time.perf_counter()-t,cpu_seconds=usage()-c);(out/'stages.json').write_text(json.dumps(rows,indent=2))
 if r.returncode:raise RuntimeError('EXECUTION: '+name)
def gate(ok,kind):
 if not ok:raise RuntimeError(kind)
try:
 stage('native_model_plan',[python,R/'generic-reflow-v2-localcanvas/code/page_pipeline.py',a.pdf,out/'native','--model-dir',root/'hybrid-prototype/mobile/PP-DocLayout-S'])
 native=json.loads((out/'native/pipeline-result.json').read_text());gate(native['source_replay_exact'] and native['source_support_failed_units']==0 and native['source_unit_bijection'],'OWNERSHIP')
 stage('glyph_capture',["node",R/'generic-reflow-v2-glyph-resources/code/probe_stateful.mjs',runtime,a.pdf,capture])
 capture_result=json.loads((capture/'result.json').read_text());gate(capture_result['observerDifference']['pixels']==0,'OBSERVER')
 bridge=out/'bridge-private.json';stage('native_bridge',[python,P/'bridge.py',plan/'plan-private.json',capture/'events-private.json',bridge])
 stage('prepare_reader',[python,P/'prepare_reader.py',plan,capture,bridge,out/'prepared'])
 stage('target_local_images',[python,P/'request_local_images.py',a.pdf,plan,out/'prepared/fallback-requests-private.json',out/'local-images'])
 gate(json.loads((out/'local-images/local-images-private.json').read_text())['all_accepted'],'TARGET_GRID')
 stage('update_local_images',[python,P/'update_local_images.py',out/'prepared/reader-data-private.json',out/'local-images/local-images-private.json',out/'updated/reader-data-private.json'])
 stage('vector_components',[python,P/'refine_vector_components.py',out/'updated/reader-data-private.json',plan/'plan-private.json',plan/'tree-reader-assets-private.json',bridge,out/'components/reader-data-private.json'])
 data=out/'final/reader-data-private.json';stage('flow_refinements',[python,P/'flow_refinements.py',out/'components/reader-data-private.json',plan/'plan-private.json',data,'--events',capture/'events-private.json','--bridge',bridge])
 stage('initial_render_28_dpr2',['node',P/'render_reader.mjs',runtime,data,out/'reader-28','28','2'])
 stage('research_html',[python,P/'make_preview.py',data,out/'research-preview-private.html'])
 result={'execution_complete':True,'accepted_reading_result':False,'visual_review_pending':True}
except Exception as e:
 result={'execution_complete':False,'accepted_reading_result':False,'failure':str(e)}
(out/'candidate-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));sys.exit(0 if result['execution_complete'] else 2)
