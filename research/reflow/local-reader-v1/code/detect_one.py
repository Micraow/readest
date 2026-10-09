"""Use installed official PP-S model only; block all network in inference."""
import os,sys,pathlib,json,socket
image,out,modeldir,cache=sys.argv[1:]
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in {'PADDLE_PDX_CACHE_HOME':cache,'MPLCONFIGDIR':cache+'/matplotlib','XDG_CACHE_HOME':cache,'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():os.environ[k]=v
def deny(*a,**k):raise RuntimeError('Network disabled during inference')
socket.socket.connect=deny;socket.create_connection=deny
from paddlex import create_model
model=create_model(model_name='PP-DocLayout-S',model_dir=modeldir,device='cpu',engine='paddle_static',engine_config={'cpu_threads':1,'run_mode':'paddle'})
r=list(model.predict(image,batch_size=1))[0].json
if isinstance(r,str):r=json.loads(r)
pathlib.Path(out).write_text(json.dumps(r))
