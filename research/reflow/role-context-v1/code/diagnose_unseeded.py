"""Read-only reconstruction of pre-fallback masks; no detector/k2 rerun or tuning."""
import ast,pathlib,json
B=pathlib.Path(__file__).resolve().parents[1]
s=ast.parse((B/'code/compose.py').read_text());items=[]
for node in s.body:
 if isinstance(node,ast.If):continue
 if isinstance(node,ast.FunctionDef) and node.name=='main':
  chosen=[]
  for st in node.body:
   chosen.append(st)
   if isinstance(st,ast.Assign) and any(isinstance(t,ast.Tuple) and any(isinstance(e,ast.Name) and e.id=='semantic_owners' for e in t.elts) for t in st.targets):break
  node.body=chosen+[ast.parse('return arr,semantic_owners,nodes,page').body[0]];node.name='diagnose'
 items.append(node)
ns={'__file__':str(B/'code/compose.py'),'__name__':'diagnostic_reconstruction'};exec(compile(ast.fix_missing_locations(ast.Module(body=items,type_ignores=[])),str(B/'code/compose.py'),'exec'),ns)
spec=next(x for x in json.loads((B/'INPUT-FREEZE.json').read_text())['inputs'] if x['key']=='Swin-v2-p04');arr,owners,nodes,page=ns['diagnose'](spec);np=ns['np'];ink=np.any(arr!=255,axis=2);ys,xs=np.where(ink&(owners==0));box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1];paint=[]
for i,(typ,b,*_) in enumerate(page.get_bboxlog()):
 bb=[v*4 for v in b]
 if ns['intersects'](bb,box):paint.append({'id':i,'type':typ,'bbox':b})
from PIL import Image
x0,y0,x1,y1=box;crop=Image.fromarray(arr).crop((max(0,x0-50),max(0,y0-80),min(arr.shape[1],x1+50),min(arr.shape[0],y1+80)));crop.save(B/'evidence/Swin-unseeded-context.png');out={'count':len(xs),'bbox_pixels':box,'intersecting_paint_envelopes':paint,'mode':'Diagnostic only; original full-page refusal remains unchanged.'};(B/'UNSEEDED-DIAGNOSIS.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
