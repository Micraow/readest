import datetime, hashlib, json, os, pathlib, resource, subprocess, time
import fitz
from PIL import Image
B=pathlib.Path(__file__).resolve().parent;V1=B.parent/'k2-reuse-v1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
NEW=[('Attention-v7-p05','Attention-v7.pdf',5),('Heisenberg-v1-p04','Heisenberg-v1.pdf',4),('FasterRCNN-v3-p03','FasterRCNN-v3.pdf',3)]
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if not (B/'evidence/reference-audit.json').exists():raise SystemExit('Independent reference audit must be frozen first')
resuming=(B/'RUN-FREEZE.json').exists()
f={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config_freeze_sha256':sha(B/'CONFIG-FREEZE.json'),'harness_binary_sha256':sha(B/'build/k2-reflow-harness'),'reference_audit_sha256':sha(B/'evidence/reference-audit.json'),'inputs':[{'key':k,'file':p,'pdf_page_1based':n,'sha256':sha(B/'inputs'/p)} for k,p,n in NEW],'paired_regression_amendment':'Approved by parent before execution on 2026-10-08 12:24 UTC. The same fixed -0.2 invocation is additionally run once on each prior page to isolate configuration effects. These four runs are paired regression, not unseen-input evidence. No further tuning is allowed based on either partition.'}
if not resuming:(B/'RUN-FREEZE.json').write_text(json.dumps(f,indent=2))
else:
    frozen=json.loads((B/'RUN-FREEZE.json').read_text())
    assert frozen['harness_binary_sha256']==f['harness_binary_sha256']
results=json.loads((B/'RUN-RESULTS.json').read_text()) if (B/'RUN-RESULTS.json').exists() else []
completed={r['key'] for r in results}
def run_one(key,partition,inp,rawdict,srcpng,render_seconds):
    out=B/'output'/(key+'.ppm');met=B/'output'/(key+'.json');start=time.monotonic()
    cmd=['timeout','--signal=TERM','--kill-after=2','60',str(B/'build/k2-reflow-harness'),str(inp),str(out),str(met)]
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    r={'key':key,'partition':partition,'returncode':proc.returncode,'render_seconds':render_seconds,'engine_process_wall_seconds':time.monotonic()-start,'source_ppm':str(inp),'rawdict':str(rawdict),'source_png':str(srcpng),'engine_stdout':proc.stdout}
    (B/'logs'/(key+'.log')).write_text(proc.stdout)
    if not proc.returncode:
      with Image.open(out) as im:
        im.save(B/'evidence'/(key+'-reflow.png'));tiles=[]
        for i,y in enumerate(range(0,im.height,844)):
          tile=Image.new('RGB',(390,844),'white');tile.paste(im.crop((0,y,390,min(im.height,y+844))))
          name=f'{key}-tile-{i+1:02d}.png';tile.save(B/'evidence'/name);tiles.append(name)
        r['tiles']=tiles
      m=json.loads(met.read_text());r.update({k:m[k] for k in ['engine_seconds','max_rss_kib','source_size','output_size','map_count']})
    results.append(r);(B/'RUN-RESULTS.json').write_text(json.dumps(results,indent=2));print(r,flush=True)
for key,p,n in NEW:
    if key in completed:continue
    t=time.monotonic();doc=fitz.open(B/'inputs'/p);page=doc[n-1];pix=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    inp=B/'inputs'/(key+'.ppm');src=B/'evidence'/(key+'-source.png');raw=B/'inputs'/(key+'-rawdict.json')
    pix.save(str(inp));pix.save(str(src));raw.write_text(json.dumps(page.get_text('rawdict'),default=lambda x:{'binary_data_omitted_for_metadata':len(x)} if isinstance(x,bytes) else str(x)))
    run_one(key,'new_input_qualification',inp,raw,src,time.monotonic()-t)
for prior in json.loads((V1/'RUN-RESULTS.json').read_text()):
    oldkey=prior['key']
    if 'paired-'+oldkey in completed:continue
    run_one('paired-'+oldkey,'paired_regression',V1/'inputs'/(oldkey+'.ppm'),V1/'inputs'/(oldkey+'-rawdict.json'),V1/'evidence'/(oldkey+'-source.png'),0)
