import os,pathlib,json,socket,time,resource
B=pathlib.Path(__file__).resolve().parents[1];W=B.parent
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for k,v in {'PADDLE_PDX_CACHE_HOME':str(W/'layout-evaluation/cache'),'MPLCONFIGDIR':str(W/'layout-evaluation/cache/matplotlib'),'XDG_CACHE_HOME':str(W/'layout-evaluation/cache'),'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PADDLE_PDX_CPU_NUM_THREADS':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items():os.environ[k]=v
def deny(*a,**k):raise RuntimeError('Network prohibited during detector inference')
socket.socket.connect=deny;socket.create_connection=deny
from paddlex import create_model
import fitz
from PIL import Image
model=create_model(model_name='PP-DocLayout-S',model_dir=str(W/'hybrid-prototype/mobile/PP-DocLayout-S'),device='cpu',engine='paddle_static',engine_config={'cpu_threads':1,'run_mode':'paddle'});rows=[]
for row in json.loads((B/'SELECTION-FREEZE.json').read_text())['pages']:
 name=row['file_name'][:-4];folder=B/'data'/name;dest=folder/'detector.json'
 if dest.exists():raise RuntimeError('Frozen detector output already exists; no rerun')
 t=time.monotonic();page=fitz.open(folder/'source.pdf')[0];pix=page.get_pixmap(matrix=fitz.Matrix(4,4),alpha=False,colorspace=fitz.csRGB);Image.frombytes('RGB',(pix.width,pix.height),pix.samples).save(folder/'native-render.png');r=list(model.predict(str(folder/'native-render.png'),batch_size=1))[0].json
 if isinstance(r,str):r=json.loads(r)
 dest.write_text(json.dumps(r));entry={'page_hash':name,'seconds':time.monotonic()-t,'candidates':len(r['res']['boxes'])};rows.append(entry);print(json.dumps(entry),flush=True)
 if entry['seconds']>60:raise RuntimeError('Page budget exceeded')
(B/'DETECTOR-RESULT.json').write_text(json.dumps({'pages':rows,'peak_self_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
