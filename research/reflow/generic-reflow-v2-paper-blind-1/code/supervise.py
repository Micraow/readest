"""Measure one complete page process family, not an execution-group average."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,time,psutil
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('sample');p.add_argument('pdf');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();here=pathlib.Path(__file__).resolve().parent
freeze=json.loads((here.parent/'FREEZE.json').read_text())
for rel,digest in freeze['files'].items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen dependency mismatch: '+rel)
out.mkdir(parents=True,exist_ok=False);cpu=min(os.sched_getaffinity(0));start=time.perf_counter();ownstart=time.process_time();before=os.getloadavg();peak=0;failure=None;sample_count=0
command=['python3',str(here/'run_candidate.py'),str(root),str(pathlib.Path(a.pdf).resolve()),str(out/'request')]
def setup():os.setsid();os.sched_setaffinity(0,{cpu})
env={**os.environ,'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','XDG_CACHE_HOME':'/tmp/generic-reflow-font-cache'}
with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
 child=subprocess.Popen(command,stdout=stdout,stderr=stderr,preexec_fn=setup,env=env)
 while True:
  done,status,usage=os.wait4(child.pid,os.WNOHANG)
  if done:child.returncode=os.waitstatus_to_exitcode(status);break
  try:
   q=psutil.Process(child.pid);rss=psutil.Process().memory_info().rss
   for x in [q]+q.children(recursive=True):
    try:rss+=x.memory_info().rss
    except psutil.Error:pass
   peak=max(peak,rss);sample_count+=1
  except psutil.Error:pass
  elapsed=time.perf_counter()-start
  if failure is None and (elapsed>60 or peak>1024**3):
   failure='BUDGET_WALL' if elapsed>60 else 'BUDGET_MEMORY';os.killpg(child.pid,signal.SIGKILL)
  time.sleep(.01)
r={'sample':a.sample,'candidate_commit':freeze['candidate_commit'],'freeze_sha256':hashlib.sha256((here.parent/'FREEZE.json').read_bytes()).hexdigest(),'wall_seconds':time.perf_counter()-start,'request_family_cpu_seconds':usage.ru_utime+usage.ru_stime,'supervisor_cpu_seconds':time.process_time()-ownstart,'peak_sampled_family_plus_supervisor_rss_mib':peak/1024**2,'rss_samples':sample_count,'exit_code':child.returncode,'failure':failure or ('EXECUTION_OR_GATE' if child.returncode else None),'cpu_affinity':[cpu],'load_before':list(before),'load_after':list(os.getloadavg()),'cold_whole_page_pipeline_attempt':True,'source_preprocessing_cache_reused':False,'filesystem_cache_flushed':False,'acquisition_and_dependency_install_excluded':True,'canonical_holdout_consumed':a.sample,'historical_component_holdout_zero_fields_invalid_for_this_run':True,'accepted_reading_result':False,'browser_tested':False,'selection_verified':False}
(out/'measurement.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
