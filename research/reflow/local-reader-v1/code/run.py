"""Bounded local PDF-to-reader research CLI. Existing official dependencies only."""
import argparse,pathlib,os,sys,json,time,subprocess,resource,hashlib
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import fitz
from PIL import Image
from export import export_page,write_reader,data
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pdf',type=pathlib.Path,required=True);p.add_argument('--pages',default='1');p.add_argument('--output-dir',type=pathlib.Path,required=True);p.add_argument('--research-root',type=pathlib.Path,default=HERE.parents[1]);p.add_argument('--paddle-python',type=pathlib.Path);p.add_argument('--layout-model',type=pathlib.Path);p.add_argument('--harness',type=pathlib.Path);a=p.parse_args();W=a.research_root.resolve();B=a.output_dir.resolve();pdf=a.pdf.resolve();page_numbers=[int(s) for s in a.pages.split(',')]
if len(page_numbers)>8 or len(set(page_numbers))!=len(page_numbers):p.error('Select 1–8 distinct pages per research run; long-document validation is pending.')
if B.exists() and any(B.iterdir()):p.error('Output directory must be empty; previous evidence is never overwritten.')
for name in ['inputs','output','evidence','logs']: (B/name).mkdir(parents=True,exist_ok=True)
py=(a.paddle_python or W/'layout-evaluation/venv/bin/python').absolute();model=(a.layout_model or W/'hybrid-prototype/mobile/PP-DocLayout-S').resolve();harness=(a.harness or W/'k2-reuse-v2-default/build/k2-reflow-harness').resolve()
for dependency in [pdf,py,model,harness]:
 if not dependency.exists():p.error('Required local dependency missing: '+str(dependency))
doc=fitz.open(pdf);pages=[];metrics=[]
for number in page_numbers:
 if not 1<=number<=len(doc):p.error('Page outside document: '+str(number))
 started=time.monotonic();page=doc[number-1];key=f'page-{number:04}';scale=4
 if page.rect.width*page.rect.height*scale*scale>16_000_000:p.error('Page exceeds this prototype raster budget; no output completeness claim.')
 pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False);image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);image.save(B/'inputs'/(key+'.png'));reason=None
 try:
  if not page.get_text().strip():raise ValueError('No native text; preserve whole page. Scan processing not qualified.')
  commands=[[str(py),str(HERE/'detect_one.py'),str(B/'inputs'/(key+'.png')),str(B/'output'/(key+'-detector.json')),str(model),str(W/'layout-evaluation/cache')],[sys.executable,str(HERE/'compose_one.py'),str(W),str(B),str(pdf),str(number),key,str(harness)]]
  for i,cmd in enumerate(commands):
   remaining=60-(time.monotonic()-started)
   if remaining<=0:raise TimeoutError('Page budget exhausted')
   with (B/'logs'/f'{key}-stage{i}.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=remaining)
  result=export_page(B,key,number)
 except (ValueError,subprocess.SubprocessError,TimeoutError,OSError) as e:
  reason=type(e).__name__+': '+str(e);display=image.copy();display.thumbnail((390,100000));result={'page':number,'source':data(image),'refused':True,'reason':'无法可靠处理，保留整页原版','pieces':[{'display':data(display),'source':data(image),'bbox':[0,0,image.width,image.height],'width':display.width,'height':display.height,'protected':True}]}
 pages.append(result);metrics.append({'page':number,'seconds':time.monotonic()-started,'whole_page_preserved':result['refused'],'processing_exception':reason,'quality_acceptance':'unverified; must audit source, relation and actual wrapping separately'})
write_reader(pages,B/'reader.html');report={'input_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'selected_pages':metrics,'source_local_only':True,'viewer':'fixed390 image reflow with high-resolution source zoom; no text selection/search/accessibility acceptance','pipeline':'frozen stroke-object-batch-v1 plus stencil-paint-v1 event support','default_order':'frozen geometry; official learned order head excluded after no measured gain','peak_self_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(B/'RUN.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
