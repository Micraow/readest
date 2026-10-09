import os,pathlib,subprocess,sys,time,json,signal
log=pathlib.Path(sys.argv[1]);report=pathlib.Path(sys.argv[2]);seconds=float(sys.argv[3]);cmd=sys.argv[4:]
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});t=time.monotonic();peak=0;reason=None
with log.open('w') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  rss=0
  for status in pathlib.Path('/proc').glob('[0-9]*/status'):
   try:
    if os.getpgid(int(status.parent.name))!=p.pid:continue
    rss+=next(int(x.split()[1]) for x in status.read_text().splitlines() if x.startswith('VmRSS:'))
   except (OSError,ProcessLookupError,StopIteration):pass
  peak=max(peak,rss)
  if rss>1048576:reason='rss_budget';os.killpg(p.pid,signal.SIGKILL);break
  if time.monotonic()-t>seconds:reason='wall_timeout';os.killpg(p.pid,signal.SIGKILL);break
  time.sleep(.1)
 code=p.wait()
result={'seconds':time.monotonic()-t,'peak_process_group_rss_kib':peak,'returncode':code,'stop_reason':reason,'rss_limit_kib':1048576,'sampling_seconds':.1,'purpose':'Post-reset reproduction; not new heldout evidence'};report.write_text(json.dumps(result,indent=2));print(json.dumps(result));sys.exit(0 if code==0 else 1)
