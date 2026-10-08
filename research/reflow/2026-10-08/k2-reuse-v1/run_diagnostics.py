import datetime, hashlib, json, os, pathlib, resource, subprocess, time
import fitz
from PIL import Image

B=pathlib.Path(__file__).resolve().parent
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
INPUTS=[
 ('Adam-v9-p03','native-structure-v1/inputs/Adam-v9-p03.pdf',3,'https://arxiv.org/pdf/1412.6980v9'),
 ('ResNet-v1-p03','native-structure-v1/inputs/ResNet-v1-p03.pdf',3,'https://arxiv.org/pdf/1512.03385v1'),
 ('Gottesman-v1-p09','hybrid-prototype/inputs/Gottesman-v1.pdf',9,'https://arxiv.org/pdf/0904.2557v1'),
 ('ForestColl-v4-p07','layout-evaluation/inputs/ForestColl.pdf',7,'https://arxiv.org/pdf/2402.06787v4'),
]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
freeze={
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'type':'Previously seen diagnostic subset, not a blind or held-out test',
 'engine_commit':'64aa9ccfcd55921c596458cb8a7197339d5f32c3',
 'engine_origin':'https://github.com/koreader/libk2pdfopt',
 'engine_logic_modified':False,
 'settings_bridge':'Uniform content-preserving overrides in settings_override.c; no per-document conditions.',
 'raster_dpi':288,'source_zoom':4,'destination_width_px':390,'destination_dpi':144,
 'maximum_columns':2,'wrap':True,'ocr_transcription':False,
 'hyphen_removal':False,'automatic_outer_crop':False,'paint_white':False,
 'gamma':1,'contrast_max':1,'sharpen':False,'dither':False,'erase_lines':False,
 'white_threshold':255,'defect_size_pts':0,'justification':'left',
 'input_regions':'Complete page; no human boxes passed to the engine',
 'run_count_per_input':1,'manual_rescue':'none',
 'limits':{'process_address_space_bytes':1024**3,'cpus':1,'page_seconds':60,'experiment_disk_bytes':1024**3},
 'quality_measure_warning':'Rectangle coverage is not evidence of content or relationship correctness. Resampling is present. No fallback may be removed from denominators.',
 'files':{str(p.relative_to(B)):sha(p) for p in [B/'settings_override.c',B/'harness.c',B/'build.py',B/'run_diagnostics.py',B/'build/k2-reflow-harness',B/'source/libk2pdfopt.tar.gz']},
 'inputs':[{'key':k,'relative_path':p,'pdf_page_1based':n,'url':u,'sha256':sha(B.parent/p)} for k,p,n,u in INPUTS],
}
freeze_path=B/'FREEZE.json'
if freeze_path.exists():raise SystemExit('Refusing a second frozen diagnostic run')
freeze_path.write_text(json.dumps(freeze,indent=2))
results=[]
for key,p,n,u in INPUTS:
    start=time.monotonic();d=fitz.open(B.parent/p);page=d[n-1]
    pix=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
    inp=B/'inputs'/(key+'.ppm'); pix.save(str(inp));pix.save(str(B/'evidence'/(key+'-source.png')))
    (B/'inputs'/(key+'-rawdict.json')).write_text(json.dumps(page.get_text('rawdict')))
    render_seconds=time.monotonic()-start
    t=time.monotonic();out=B/'output'/(key+'.ppm');met=B/'output'/(key+'.json')
    cmd=['timeout','--signal=TERM','--kill-after=2','60',str(B/'build/k2-reflow-harness'),str(inp),str(out),str(met)]
    run=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    wall=time.monotonic()-t;(B/'logs'/(key+'.log')).write_text(run.stdout)
    r={'key':key,'returncode':run.returncode,'render_seconds':render_seconds,'engine_process_wall_seconds':wall,'engine_stdout':run.stdout}
    if run.returncode==0:
        with Image.open(out) as im:
            im.save(B/'evidence'/(key+'-reflow.png'))
            tiles=[]
            for i,y in enumerate(range(0,im.height,844)):
                tile=Image.new('RGB',(390,844),'white');tile.paste(im.crop((0,y,390,min(y+844,im.height))))
                name=f'{key}-tile-{i+1:02d}.png';tile.save(B/'evidence'/name);tiles.append(name)
            r['tiles']=tiles
        m=json.loads(met.read_text());r.update({k:m[k] for k in ['engine_seconds','max_rss_kib','source_size','output_size','map_count']})
    results.append(r);(B/'RUN-RESULTS.json').write_text(json.dumps(results,indent=2));print(r,flush=True)
