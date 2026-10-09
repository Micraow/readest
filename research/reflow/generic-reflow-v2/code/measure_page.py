"""One fresh page process; one allowed CPU; wall/RSS enforcement and honest costs."""
import argparse,json,os,pathlib,subprocess,sys,time
import psutil

def run(pdf,out):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);cpu=min(os.sched_getaffinity(0));start=time.perf_counter()
 def setup():os.sched_setaffinity(0,{cpu})
 cmd=[sys.executable,str(pathlib.Path(__file__).with_name('prototype.py')),str(pdf),str(out)]
 with (out/'stdout.json').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
  child=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,preexec_fn=setup);peak=0;peak_cpu=0;failure=None
  while True:
   finished,status,usage=os.wait4(child.pid,os.WNOHANG)
   if finished:
    child.returncode=os.waitstatus_to_exitcode(status);break
   try:
    process=psutil.Process(child.pid);family=[process]+process.children(recursive=True);peak=max(peak,sum(p.memory_info().rss for p in family if p.is_running()));peak_cpu=max(peak_cpu,sum(sum(p.cpu_times()[:2]) for p in family if p.is_running()))
   except psutil.Error:pass
   if time.perf_counter()-start>60:failure='wall_timeout';os.kill(child.pid,9)
   if peak>1024**3:failure='rss_limit';os.kill(child.pid,9)
   time.sleep(.01)
 wall=time.perf_counter()-start
 if child.returncode and failure is None:failure='process_exit' 
 result=dict(cpu_affinity=[cpu],cold_page_process_wall_seconds=wall,sampled_peak_family_rss_mib=peak/1024**2,sampled_cpu_seconds=peak_cpu,exit_code=child.returncode,failure=failure,process_cpu_seconds=usage.ru_utime+usage.ru_stime,process_peak_rss_mib=usage.ru_maxrss/1024,inputs='already-local PDF bytes; no download cost; OS file cache not flushed',included='Python interpreter/import, PDF open, extraction, planning, two base raster passes, per-local-object isolated raster passes, asset encode, HTML and audit writes',excluded='browser startup/load/paint and interactive audit; cannot claim interactive-page budget')
 if child.returncode==0 and (out/'audit.json').exists():
  audit=json.loads((out/'audit.json').read_text());result['hot_pipeline_seconds']=audit['hot_pipeline_seconds']
 (out/'measurement.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('out');a=p.parse_args();run(a.pdf,a.out)
