"""One preregistered complete request; no restart or partial result promoted to pass."""
import argparse,json,pathlib,subprocess,time,resource,os,signal,hashlib
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
command=[str(root/'layout-evaluation/venv/bin/python'),str(root/'readest-research-checkpoint/research/reflow/generic-reflow-v2-integrated-paper-1/code/run_cold_page.py'),str(root),str(pathlib.Path(a.pdf).resolve()),str(out/'request')]
record={'command':command,'wall_limit_seconds':60,'retries':0,'pipeline':'unchanged integrated-paper-1','wrapper_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()};start=time.perf_counter();timed_out=False
with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
 child=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
 try:code=child.wait(timeout=60)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(child.pid,signal.SIGTERM)
  try:code=child.wait(timeout=2)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
usage=resource.getrusage(resource.RUSAGE_CHILDREN);record.update(wall_seconds=time.perf_counter()-start,child_cpu_seconds=usage.ru_utime+usage.ru_stime,exit_code=code,timed_out=timed_out,execution_pass=not timed_out and code==0,browser_verified=False)
(out/'execution.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
