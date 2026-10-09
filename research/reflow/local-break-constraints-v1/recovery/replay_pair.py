import pathlib,json,subprocess,time,os,sys
W=pathlib.Path(__file__).resolve().parents[1];B=W/'local-break-constraints-v1';pair=int(sys.argv[1]);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');py=str(W/'layout-evaluation/venv/bin/python');rows=[]
for p in json.loads((B/'INPUT-SELECTION.json').read_text())['pages']:
 if p['pair']!=pair:continue
 key=p['key']
 for arm,script in [('AB',B/'code/run_page.py'),('E',W/'readest-recovery/run_no_font_hint.py'),('CD',B/'code/baseline_cd.py')]:
  log=B/'output'/(key+'-'+arm+'-replay.log')
  if log.exists():raise RuntimeError('No unlabelled rerun '+str(log))
  cmd=[py,str(script),key] if arm=='CD' else [py,str(script),str(B/'inputs'/(key+'.pdf')),str(B/'output'/(key+'-detector.json')),str(B/'output'/(key+'-'+arm)),'--key',key]
  t=time.monotonic()
  with log.open('w') as f:
   try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60,env=env);code=r.returncode
   except subprocess.TimeoutExpired:code=124
  row={'key':key,'arm':arm,'elapsed_seconds':time.monotonic()-t,'returncode':code};rows.append(row);(W/'readest-recovery'/f'PAIR-{pair}-REPLAY.json').write_text(json.dumps({'scope':'Post-reset reproduction of frozen candidate; source already seen, not fresh generalization','base_commit':'9f6b88cfa9b15169f7d739b10c350efa261e19dd','rows':rows},indent=2));print(json.dumps(row),flush=True)
