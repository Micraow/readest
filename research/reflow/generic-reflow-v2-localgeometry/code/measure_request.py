"""Linux request supervisor: same CPU including observer; reap killed descendants."""
import argparse,ctypes,json,os,pathlib,signal,subprocess,time,psutil
p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--wall-limit',type=float,default=60);p.add_argument('--cold-complete-page',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
# Process-local orphan reaping, not a machine/security configuration change.
if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER failed')
cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu});own=psutil.Process();start=time.perf_counter();ownstart=time.process_time();before=os.getloadavg();peak=0;failure=None;usage_sum=0.;reaped=[];root_status=None
with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
 child=subprocess.Popen(a.command,stdout=stdout,stderr=stderr,start_new_session=True,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
 while True:
  no_children=False
  while True:
   try:pid,status,usage=os.wait4(-1,os.WNOHANG)
   except ChildProcessError:no_children=True;break
   if not pid:break
   elapsed_cpu=usage.ru_utime+usage.ru_stime;usage_sum+=elapsed_cpu;reaped.append({'pid':pid,'exit_code':os.waitstatus_to_exitcode(status),'wait4_cpu_seconds_including_waited_descendants':elapsed_cpu})
   if pid==child.pid:root_status=os.waitstatus_to_exitcode(status);child.returncode=root_status
  if no_children:break
  rss=own.memory_info().rss
  for q in own.children(recursive=True):
   try:rss+=q.memory_info().rss
   except psutil.Error:pass
  peak=max(peak,rss);wall=time.perf_counter()-start
  if failure is None and (wall>a.wall_limit or peak>1024**3):
   failure='BUDGET_WALL' if wall>a.wall_limit else 'BUDGET_MEMORY'
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  time.sleep(.05)
wall=time.perf_counter()-start;supervisor=time.process_time()-ownstart;r={'wall_seconds':wall,'request_family_cpu_seconds':usage_sum,'supervisor_cpu_seconds':supervisor,'total_accounted_cpu_seconds':usage_sum+supervisor,'peak_sampled_family_plus_supervisor_rss_mib':peak/1024**2,'exit_code':root_status,'failure':failure or ('process_exit' if root_status else None),'request_and_supervisor_cpu_affinity':[cpu],'cpu_accounting':'wait4 of root and subreaper-adopted orphan descendants; each waited subtree counted once, plus supervisor process time','sampling_interval_seconds':.05,'reaped_processes':reaped,'load_before':list(before),'load_after':list(os.getloadavg()),'cold_complete_page_request':a.cold_complete_page,'cached_or_partial_stage':not a.cold_complete_page,'filesystem_cache_flushed':False};(out/'measurement.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
