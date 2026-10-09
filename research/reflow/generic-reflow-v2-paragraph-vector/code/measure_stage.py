"""Bound one explicit subprocess stage; never label a cached stage cold-page cost."""
import argparse,json,os,pathlib,subprocess,time,psutil
p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);cpu=min(os.sched_getaffinity(0));start=time.perf_counter();before=os.getloadavg();peak=0;failure=None
if (out/'measurement.json').exists():raise FileExistsError('refuse evidence overwrite')
def setup():os.setsid();os.sched_setaffinity(0,{cpu})
with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
 child=subprocess.Popen(a.command,stdout=stdout,stderr=stderr,preexec_fn=setup)
 while True:
  done,status,usage=os.wait4(child.pid,os.WNOHANG)
  if done:child.returncode=os.waitstatus_to_exitcode(status);break
  try:
   q=psutil.Process(child.pid);peak=max(peak,sum(x.memory_info().rss for x in [q]+q.children(recursive=True) if x.is_running()))
  except psutil.Error:pass
  if failure is None and (time.perf_counter()-start>60 or peak>1024**3):failure='wall_timeout' if time.perf_counter()-start>60 else 'memory_limit';os.killpg(child.pid,9)
  time.sleep(.01)
r={'wall_seconds':time.perf_counter()-start,'cpu_seconds':usage.ru_utime+usage.ru_stime,'peak_family_rss_mib':peak/1024**2,'exit_code':child.returncode,'failure':failure or ('process_exit' if child.returncode else None),'cpu_affinity':[cpu],'load_before':list(before),'load_after':list(os.getloadavg()),'cold_whole_page_pipeline':False,'source_preprocessing_cache_reused':True,'filesystem_cache_flushed':False};(out/'measurement.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
