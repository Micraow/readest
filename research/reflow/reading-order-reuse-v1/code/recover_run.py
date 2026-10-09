"""Recover metadata from saved predictions after JSON NumPy-scalar failure; no inference."""
import pathlib,json,ast,re,hashlib
import numpy as np
B=pathlib.Path(__file__).resolve().parents[1];P=B.parent/'stroke-object-batch-v1';lines=(B/'logs/model.log').read_text().splitlines();progress={}
for s in lines:
 if s.startswith("{'key':"):
  r=ast.literal_eval(re.sub(r'np.int64\((-?[0-9]+)\)',r'\1',s));progress[r['key']]=r
monitor=json.loads(next(s.removeprefix('RESOURCE_MONITOR ') for s in lines if s.startswith('RESOURCE_MONITOR ')));rows=[]
for inp in json.loads((P/'INPUT-FREEZE.json').read_text())['inputs']:
 key=inp['key'];r=progress[key];z=np.load(B/'output'/(key+'-order.npz'));selected=[(i,b) for i,b in enumerate(json.loads((P/'output'/(key+'-detector.json')).read_text())['res']['boxes']) if b['score']>=.5];r.update({'detector_ids':[i for i,b in selected],'labels':[b['label'] for i,b in selected],'model_order_detector_ids':[selected[int(j)][0] for j in np.argsort(z['ranks'])],'prediction_sha256':hashlib.sha256((B/'output'/(key+'-order.npz')).read_bytes()).hexdigest()});rows.append(r)
out={'model_revision':json.loads((B/'MODEL-METADATA.json').read_text())['revision'],'loaded_parameters':20743304,'rows':rows,'external_resource_monitor':monitor,'weights_load_seconds':None,'status':'All8ordinary and8reversed-input inferences completed with saved logits. Final JSON serialization failed on a NumPy scalar; this file reconstructed without rerunning inference. Dedicated weights-load timer was not recoverable.','scope':'Order-only benchmark on PP-S candidates; upstream training overlap unknown; no reading-quality claim from latency or input-order stability.'};(B/'RUN-RESULT.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='rows'})
