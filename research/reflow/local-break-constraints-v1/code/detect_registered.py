"""One frozen batch of real raster inputs; no test reference labels are read."""
import os,pathlib,json,socket,time,resource
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent;t0=time.monotonic();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in {'PADDLE_PDX_CACHE_HOME':str(W/'layout-evaluation/cache'),'MPLCONFIGDIR':str(W/'layout-evaluation/cache/matplotlib'),'XDG_CACHE_HOME':str(W/'layout-evaluation/cache'),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():os.environ[k]=v
def deny(*a,**k):raise RuntimeError('Network disabled during inference')
socket.socket.connect=deny;socket.create_connection=deny
from paddlex import create_model
import fitz
from PIL import Image
model=create_model(model_name='PP-DocLayout-S',model_dir=str(W/'hybrid-prototype/mobile/PP-DocLayout-S'),device='cpu',engine='paddle_static',engine_config={'cpu_threads':1,'run_mode':'paddle'});cold=time.monotonic()-t0;rows=[]
for row in json.loads((B/'INPUT-SELECTION.json').read_text())['pages']:
 key=row['key'];dest=B/'output'/(key+'-detector.json')
 if dest.exists():raise RuntimeError('Registered output exists; refuse rerun')
 t=time.monotonic();page=fitz.open(B/'inputs'/(key+'.pdf'))[0];pix=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);image=B/'inputs'/(key+'-native.png');im.save(image);r=list(model.predict(str(image),batch_size=1))[0].json
 if isinstance(r,str):r=json.loads(r)
 dest.write_text(json.dumps(r));rows.append({'key':key,'raster_encode_inference_seconds':time.monotonic()-t,'candidates':len(r['res']['boxes'])});print(json.dumps(rows[-1]),flush=True)
 if rows[-1]['raster_encode_inference_seconds']>60:raise RuntimeError('Page budget exceeded')
(B/'DETECTOR-RESULT.json').write_text(json.dumps({'cold_init_seconds':cold,'pages':rows,'total_seconds':time.monotonic()-t0,'peak_self_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
