"""Fresh-process A-B-B-A; every measured request remains separately reportable."""
import argparse,hashlib,json,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('pdf');p.add_argument('out');a=p.parse_args();root=pathlib.Path(a.root).resolve();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False);R=root/'readest-research-checkpoint/research/reflow';python=root/'layout-evaluation/venv/bin/python';measure=R/'generic-reflow-v2-localgeometry/code/measure_request.py';old=R/'generic-reflow-v2-order-tree/code/predict_local_regions.py';new=pathlib.Path(__file__).with_name('direct_prior.py');rows=[];canonical=None;image=None
for index,mode in enumerate(['baseline','direct','direct','baseline']):
 dest=out/(str(index)+'-'+mode);cost=out/(str(index)+'-'+mode+'-cost');cmd=[python,measure,'--wall-limit','60',cost,python,old if mode=='baseline' else new,pathlib.Path(a.pdf).resolve(),dest,root/'hybrid-prototype/mobile/PP-DocLayout-S'];result=subprocess.run([str(x) for x in cmd],capture_output=True,text=True);(out/(str(index)+'-supervisor.stdout')).write_text(result.stdout);(out/(str(index)+'-supervisor.stderr')).write_text(result.stderr)
 row={'ordinal':index,'mode':mode,'supervisor_exit':result.returncode};measurement=json.loads((cost/'measurement.json').read_text()) if (cost/'measurement.json').exists() else {};row['cost']=measurement
 if (dest/'prediction-private.json').exists():
  boxes=json.loads((dest/'prediction-private.json').read_text())['res']['boxes'];content=json.dumps(boxes,separators=(',',':'));pnghash=hashlib.sha256((dest/'native-model-input.png').read_bytes()).hexdigest()
  if canonical is None:canonical=content;image=pnghash
  row.update(prediction_count=len(boxes),ordered_boxes_exact=content==canonical,native_input_exact=pnghash==image,boxes_sha256=hashlib.sha256(content.encode()).hexdigest(),stages=json.loads((dest/'model-costs.json').read_text()))
 else:row.update(ordered_boxes_exact=False,native_input_exact=False)
 rows.append(row);(out/'paired-result-private.json').write_text(json.dumps({'runs':rows,'all_equivalent':all(r['ordered_boxes_exact'] and r['native_input_exact'] and r['cost'].get('exit_code')==0 for r in rows),'whole_page_budget_measured':False},indent=2));print(json.dumps({k:row[k] for k in ['ordinal','mode','ordered_boxes_exact','native_input_exact','cost']}),flush=True)
