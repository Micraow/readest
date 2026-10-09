"""Original adapter for the official PaddleX reading-order submodule only."""
import os
for k,v in {'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1'}.items():os.environ[k]=v
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import pathlib,json,time,resource,hashlib,importlib.metadata,socket
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent
if (B/'RUN-STARTED.json').exists():raise SystemExit('Frozen model benchmark already started')
(B/'RUN-STARTED.json').write_text(json.dumps({'epoch':time.time(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}))
def deny(*a,**k):raise RuntimeError('Network disabled during model benchmark')
socket.socket.connect=deny;socket.create_connection=deny
start=time.monotonic()
import numpy as np
os.environ['PADDLE_PDX_CACHE_HOME']=str(W/'layout-evaluation/cache')
os.environ['XDG_CACHE_HOME']=str(W/'layout-evaluation/cache')
os.environ['MPLCONFIGDIR']=str(W/'layout-evaluation/cache/matplotlib')
import paddle
from safetensors import safe_open
from paddlex.inference.models.object_detection.modeling import pp_doclayout_v2 as official
from paddlex.inference.models.object_detection.modeling._config_pp_doclayout_v2 import PPDocLayoutV2ReadingOrderConfig
cfg=json.loads((B/'model/config.json').read_text());model=official.PPDocLayoutV2ReadingOrder(PPDocLayoutV2ReadingOrderConfig(**cfg['reading_order_config']));model.eval();state=model.state_dict();metadata=json.loads((B/'READING-ORDER-TENSOR-METADATA.json').read_text());fullkeys=list(metadata['tensors']);incoming={k.removeprefix('reading_order.') for k in fullkeys}
if set(state)!=incoming:raise RuntimeError('Parameter names differ: missing='+str(set(state)-incoming)+' extra='+str(incoming-set(state)))
class KeyOnly:
 def get_hf_state_dict(self):return dict.fromkeys(fullkeys)
transpose=set(official.PPDocLayoutV2.get_transpose_weight_keys(KeyOnly()));loaded=0
with safe_open(str(B/'model/model.safetensors'),framework='np') as f:
 for full in fullkeys:
  key=full.removeprefix('reading_order.');array=f.get_tensor(full)
  if full in transpose:array=array.T
  if list(array.shape)!=list(state[key].shape):raise RuntimeError('Parameter shape mismatch '+key)
  state[key].set_value(array);loaded+=int(array.size)
 del array
load_seconds=time.monotonic()-start
# Fixed mapping: PP-S formula denotes display math (V2 class15), not inline class5.
label_map={v:int(k) for k,v in cfg['id2label'].items()};label_map.update({'formula':15,'text':22,'header':12,'footer':8,'header_image':13,'footer_image':9,'chart_title':7,'table_title':7})
class_order=cfg['class_order'];rows=[]
from PIL import Image
for inp in json.loads((W/'stroke-object-batch-v1/INPUT-FREEZE.json').read_text())['inputs']:
 key=inp['key'];P=W/'stroke-object-batch-v1';boxes=json.loads((P/'output'/(key+'-detector.json')).read_text())['res']['boxes'];selected=[(i,x) for i,x in enumerate(boxes) if x['score']>=.5];unknown=[x['label'] for i,x in selected if x['label'] not in label_map]
 if unknown:rows.append({'key':key,'unsupported_labels':unknown,'failed':True});continue
 with Image.open(P/'inputs'/(key+'.png')) as image:width,height=image.size
 coords=np.array([x['coordinate'] for i,x in selected],np.float32);coords=coords/np.array([width,height,width,height],np.float32)*1000;coords=np.clip(coords,0,1000);labels=np.array([class_order[label_map[x['label']]] for i,x in selected],np.int64);N=len(selected)
 def infer(c,l):
  with paddle.no_grad():
   scores=model(paddle.to_tensor(c[None]),paddle.to_tensor(l[None]),paddle.ones([1,N],dtype='bool'));ranks,votes=official.get_order(scores)
  return scores.numpy()[0],ranks.numpy()[0],votes.numpy()[0]
 t=time.monotonic();logits,ranks,votes=infer(coords,labels);seconds=time.monotonic()-t
 reverse=np.arange(N-1,-1,-1);_,rev_ranks,_=infer(coords[reverse],labels[reverse]);unpermuted=np.empty(N,np.int64);unpermuted[reverse]=rev_ranks
 inversions=sum((ranks[i]<ranks[j])!=(unpermuted[i]<unpermuted[j]) for i in range(N) for j in range(i+1,N));np.savez(B/'output'/(key+'-order.npz'),logits=logits,ranks=ranks,votes=votes,reverse_unpermuted_ranks=unpermuted)
 rows.append({'key':key,'partition':inp['partition'],'candidates':N,'detector_ids':[i for i,x in selected],'labels':[x['label'] for i,x in selected],'model_order_detector_ids':[selected[j][0] for j in np.argsort(ranks)],'seconds':seconds,'reversal_pairwise_disagreements':inversions,'pair_count':N*(N-1)//2,'failed':False});print({k:v for k,v in rows[-1].items() if k not in ['labels','detector_ids','model_order_detector_ids']},flush=True)
versions={n:importlib.metadata.version(n) for n in ['paddlepaddle','paddlex','safetensors','numpy']};out={'model_revision':json.loads((B/'MODEL-METADATA.json').read_text())['revision'],'loaded_parameters':loaded,'weights_load_seconds':load_seconds,'wall_seconds':time.monotonic()-start,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'versions':versions,'rows':rows,'official_implementation_sha256':hashlib.sha256(pathlib.Path(official.__file__).read_bytes()).hexdigest(),'scope':'Order-only subnetwork on unchanged PP-S proposal boxes/classes. No OCR/text generation, role training, renderer replacement or end-to-end fidelity claim.'};(B/'RUN-RESULT.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='rows'},flush=True)
