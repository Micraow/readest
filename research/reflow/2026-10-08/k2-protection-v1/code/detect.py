import os,pathlib,socket,json,time,resource,sys
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in {'PADDLE_PDX_CACHE_HOME':str(W/'layout-evaluation/cache'),'MPLCONFIGDIR':str(W/'layout-evaluation/cache/matplotlib'),'XDG_CACHE_HOME':str(W/'layout-evaluation/cache'),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():os.environ[k]=v
def deny(*a,**k):raise RuntimeError('Network prohibited during local inference')
socket.socket.connect=deny;socket.create_connection=deny
start=time.monotonic()
from paddlex import create_model
model=create_model(model_name='PP-DocLayout-S',model_dir=str(W/'hybrid-prototype/mobile/PP-DocLayout-S'),device='cpu',engine='paddle_static',engine_config={'cpu_threads':1,'run_mode':'paddle'})
load=time.monotonic()-start;rows=[]
for inp in json.loads((B/'INPUT-FREEZE.json').read_text())['inputs']:
    k=inp['key'];t=time.monotonic();r=list(model.predict(str(B/'inputs'/(k+'.png')),batch_size=1))[0].json
    if isinstance(r,str):r=json.loads(r)
    (B/'output'/(k+'-detector.json')).write_text(json.dumps(r,indent=2))
    row={'key':k,'inference_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};rows.append(row);print(row,flush=True)
(B/'DETECTOR-METRICS.json').write_text(json.dumps({'load_seconds':load,'pages':rows},indent=2))
