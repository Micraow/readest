"""Enforce single CPU and an RSS safety margin for a child process group."""
import os,subprocess,sys,time,json,pathlib,signal
limit=960*1024 # KiB; stop below 1 GiB
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
p=subprocess.Popen(sys.argv[1:],start_new_session=True);start=time.monotonic();peak=0;reason=None
while p.poll() is None:
    rss=0
    for stat in pathlib.Path('/proc').glob('[0-9]*/stat'):
      try:
        # Linux /proc stat fields: pgrp=5, rss=24. Names in parentheses may include spaces.
        z=stat.read_text();a=z[z.rfind(')')+2:].split()
        if int(a[2])==p.pid:rss+=int(a[21])*os.sysconf('SC_PAGE_SIZE')//1024
      except (OSError,ValueError,IndexError):pass
    peak=max(peak,rss)
    if rss>limit:reason='RSS safety margin exceeded'
    if time.monotonic()-start>60:reason='60-second process limit exceeded'
    if reason:os.killpg(p.pid,signal.SIGTERM);break
    time.sleep(.02)
try:code=p.wait(timeout=3)
except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
out={'seconds':time.monotonic()-start,'peak_group_rss_kib':peak,'returncode':code,'stopped_reason':reason,'rss_stop_threshold_kib':limit,'cpu_affinity':list(os.sched_getaffinity(0))}
print('RESOURCE_MONITOR '+json.dumps(out),flush=True);sys.exit(code if code>=0 else 1)
