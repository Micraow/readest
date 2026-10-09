"""One CPU, bounded fresh native Node glyph-resource diagnostic."""
import argparse,json,os,pathlib,subprocess,time
import psutil
p=argparse.ArgumentParser();p.add_argument('runtime');p.add_argument('pdf');p.add_argument('out');p.add_argument('--script',default='probe.mjs');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);
if (out/'measurement.json').exists():raise FileExistsError('refusing to overwrite prior evidence')
cpu=min(os.sched_getaffinity(0));start=time.perf_counter();load=os.getloadavg()
def setup():os.setsid();os.sched_setaffinity(0,{cpu})
with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
 child=subprocess.Popen(['node',str(pathlib.Path(__file__).with_name(a.script)),a.runtime,a.pdf,a.out],stdout=stdout,stderr=stderr,preexec_fn=setup);peak=0;failure=None
 while True:
  finished,status,usage=os.wait4(child.pid,os.WNOHANG)
  if finished:child.returncode=os.waitstatus_to_exitcode(status);break
  try:
   process=psutil.Process(child.pid);peak=max(peak,sum(x.memory_info().rss for x in [process]+process.children(recursive=True) if x.is_running()))
  except psutil.Error:pass
  if time.perf_counter()-start>60:failure='wall_timeout';os.killpg(child.pid,9)
  elif peak>1024**3:failure='rss_limit';os.killpg(child.pid,9)
  time.sleep(.01)
r=dict(script=a.script,wall_seconds=time.perf_counter()-start,cpu_seconds=usage.ru_utime+usage.ru_stime,peak_family_rss_mib=peak/1024**2,cpu_affinity=[cpu],load_before=list(load),load_after=list(os.getloadavg()),exit_code=child.returncode,failure=failure or ('process_exit' if child.returncode else None),included='fresh Node imports, PDF/font load, native baseline, glyph extraction, native auxiliary passes, resource replay, untouched-engine comparison, script-specific native relocation tests and evidence encoding',excluded='dependency download/install, region/paragraph reflow, actual browser, UI selection/font/zoom; not a reflow page cost',file_cache_flushed=False)
if (out/'result.json').exists():r['probe']=json.loads((out/'result.json').read_text())
(out/'measurement.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
