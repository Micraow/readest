import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[n]='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import pathlib,json,time,resource,hashlib
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
import fitz
from envelope import inspect
B=pathlib.Path(__file__).resolve().parents[1]
def fixtures():
 d=fitz.open()
 for i in range(8):
  p=d.new_page(width=320,height=420);p.insert_text((35.25,70.75),'Original source jgy A = b + c',fontname='tiit',fontsize=17)
  p.insert_text((70.125,160.375),'\u221a',fontname='symb',fontsize=55)
  p.insert_text((115.2,145.8),'x + y',fontname='tiro',fontsize=16)
  if i==1:p.insert_text((60.3,245.7),'Italic glyph bearings',fontname='tiit',fontsize=23,morph=(fitz.Point(60.3,245.7),fitz.Matrix(17)))
  if i==2:p.insert_text((33.2,255.4),'STROKE',fontsize=35,render_mode=1,border_width=2.3,color=(.1,.2,.8))
  if i==3:
   q=fitz.open();q.new_page(width=220,height=100).insert_text((0,55),'CLIPPED FORM abcdefgh',fontsize=25);p.show_pdf_page(fitz.Rect(50.3,220.4,180.8,270.9),q,0,clip=fitz.Rect(40.2,20.3,160.7,70.8))
  if i==4:p.set_cropbox(fitz.Rect(20.3,30.2,290.8,390.7))
  if i==5:p.set_rotation(90)
  if i==6:p.draw_rect(fitz.Rect(55.1,200.2,215.7,245.4),fill=(.1,.3,.9),color=(.8,.1,.1),width=4,fill_opacity=.55)
  if i==7:
   a=p.add_freetext_annot(fitz.Rect(35,280,230,325),'Visible annotation',fontsize=16,text_color=(.9,0,.1));a.update()
 d.save(B/'inputs/synthetic.pdf');return d
if __name__=='__main__':
 if (B/'RUN-STARTED.json').exists():raise SystemExit('Frozen single pass already started')
 (B/'RUN-STARTED.json').write_text(json.dumps({'epoch':time.time(),'code':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'code').glob('*.py')}}));start=time.monotonic();rows=[];doc=fixtures()
 for i,p in enumerate(doc):
  for scale in [1.25,4.]:
   t=time.monotonic();pix,r=inspect(p,scale);r.update({'key':f'original-fixture-{i}','seconds':time.monotonic()-t});rows.append(r);pix.save(str(B/'evidence'/f'fixture-{i}-{scale}.png'))
 # This prior paper is a seen mechanism regression, never held-out evidence.
 p=fitz.open(B.parent/'k2-anchor-v1/inputs/GroupNorm-v3.pdf')[2];t=time.monotonic();pix,r=inspect(p,4);r.update({'key':'GroupNorm-v3-p03-seen-regression','seconds':time.monotonic()-t});rows.append(r)
 full={'rows':rows,'wall_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};(B/'output/PRIVATE-RESULT.json').write_text(json.dumps(full,indent=2));public={**full,'rows':[{k:v for k,v in r.items() if k!='paints'} for r in rows]};(B/'RESULT.json').write_text(json.dumps(public,indent=2));print(json.dumps(public,indent=2))
