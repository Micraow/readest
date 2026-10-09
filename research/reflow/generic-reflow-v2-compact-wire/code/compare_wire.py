import argparse,json,pathlib,time,os,math,io
from compact_wire import CompactJSON
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('out');a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});facade=CompactJSON('control');cases=[None,True,1,-0.,1.0000000000000002,'汉字 e\u0301 \\ ",',{ 'nested':[1,False,{},[],{'x':'\u2028'}],'ordered':{'z':1,'a':2}}];checks=[]
for case in cases:
 for ascii in [False,True]:
  plain=json.dumps(case,ensure_ascii=ascii,indent=2);compact=facade.dumps(case,ensure_ascii=ascii,indent=2);assert json.loads(plain)==json.loads(compact);checks.append(True)
assert facade.dumps(-0.)=='-0.0';assert facade.loads('1')==1
for serializer in [json,facade]:
 try:serializer.dumps(float('nan'),allow_nan=False);raise AssertionError('nonfinite accepted')
 except ValueError:pass
 buf=io.StringIO();serializer.dump({'key':[1,2]},buf,indent=2);assert json.loads(buf.getvalue())=={'key':[1,2]}
original=pathlib.Path(a.plan).read_text();expected=json.loads(original);rows=[]
for mode in ['pretty','compact','compact','pretty']:
 start=time.perf_counter();cpu=time.process_time();parsed=json.loads(pathlib.Path(a.plan).read_text());encoded=(json if mode=='pretty' else facade).dumps(parsed,ensure_ascii=False,indent=2);dest=out/(str(len(rows))+'-'+mode+'.json');dest.write_text(encoded);same=json.loads(dest.read_text())==expected;assert same;rows.append({'mode':mode,'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu,'bytes':dest.stat().st_size,'decoded_values_exact':same,'load':list(os.getloadavg())})
result={'authored_cases':len(checks),'negative_zero_preserved':True,'nonfinite_error_preserved':True,'runs':rows,'full_page_cost':False};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
