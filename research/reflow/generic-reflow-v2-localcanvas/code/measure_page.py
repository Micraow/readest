"""One fresh page process; one allowed CPU; wall/RSS enforcement and honest costs."""
import argparse,json,os,pathlib,subprocess,sys,time
import psutil

def run(pdf,out,extra=()):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);cpu=min(os.sched_getaffinity(0));start=time.perf_counter();load_before=os.getloadavg()
 def setup():os.setsid();os.sched_setaffinity(0,{cpu})
 cmd=[sys.executable,str(pathlib.Path(__file__).with_name('page_pipeline.py')),str(pdf),str(out),*extra]
 with (out/'stdout.json').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
  child=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,preexec_fn=setup);peak=0;peak_cpu=0;failure=None
  while True:
   finished,status,usage=os.wait4(child.pid,os.WNOHANG)
   if finished:
    child.returncode=os.waitstatus_to_exitcode(status);break
   try:
    process=psutil.Process(child.pid);family=[process]+process.children(recursive=True);peak=max(peak,sum(p.memory_info().rss for p in family if p.is_running()));peak_cpu=max(peak_cpu,sum(sum(p.cpu_times()[:2]) for p in family if p.is_running()))
   except psutil.Error:pass
   if time.perf_counter()-start>60:failure='wall_timeout';os.killpg(child.pid,9)
   if peak>1024**3:failure='rss_limit';os.killpg(child.pid,9)
   time.sleep(.01)
 wall=time.perf_counter()-start
 if child.returncode and failure is None:failure='process_exit'
 result=dict(load_before=list(load_before),load_after=list(os.getloadavg()),shared_environment_not_isolated=True,cpu_affinity=[cpu],cold_page_process_wall_seconds=wall,sampled_peak_family_rss_mib=peak/1024**2,sampled_cpu_seconds=peak_cpu,exit_code=child.returncode,failure=failure,process_cpu_seconds=usage.ru_utime+usage.ru_stime,process_peak_rss_mib=usage.ru_maxrss/1024,inputs='already-local PDF bytes; no download cost; OS file cache not flushed',included='fresh Python/imports, PDF open per phase, native inventory/planning, stable text alpha extraction and encoding, bounded within/cross-object and graphic/fraction closure, optional cold live layout inference, full native masked replay, hierarchical region/paragraph flow, all local unit native render/encode and inline composition, HTML and final audit writes; excludes ink annotations by amended user scope',excluded='browser startup/load/paint and interactive audit; cannot claim interactive-page budget')
 if child.returncode==0 and (out/'pipeline-result.json').exists():
  result['pipeline']=json.loads((out/'pipeline-result.json').read_text())
 (out/'measurement.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');a,extra=p.parse_known_args();run(a.pdf,a.out,extra)
