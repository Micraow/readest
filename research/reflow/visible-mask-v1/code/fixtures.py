import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[n]='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import pathlib,json,time,hashlib,resource
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
import numpy as np
from PIL import Image,ImageDraw
from masks import partition
B=pathlib.Path(__file__).resolve().parents[1]
def fixture(kind):
 # Ordered source operations are actually composited before masks are inferred.
 im=Image.new('RGB',(360,220),'white');draw=ImageDraw.Draw(im)
 draw.rectangle((0,0,359,219),fill='white') # broad background is not a semantic parent
 draw.line([(45,75),(62,92),(76,42),(135,42)],fill='black',width=5)
 draw.text((220,70),'LATER BODY',fill='black')
 boxes=[[38,38,141,65],[216,66,302,86]];expect='accept'
 if kind=='white_overpaint':
  draw.rectangle((90,35,145,55),fill='white') # removes old visible ink; no resurrection
 if kind=='late_separate_text':
  draw.rectangle((0,120,359,219),fill='white');draw.text((46,160),'AFTER BACKGROUND',fill='black');boxes.append([42,156,145,177])
 if kind=='transparent_overlay':
  overlay=Image.new('RGBA',im.size,(0,0,0,0));ImageDraw.Draw(overlay).rectangle((40,45,95,110),fill=(0,0,220,130));im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB');boxes.append([40,45,95,110]);expect='refuse'
 if kind=='touching_distinct_objects':
  draw.line([(130,42),(220,75)],fill='black',width=5);expect='refuse'
 if kind=='unseeded_dot':draw.ellipse((178,160,185,167),fill='black');expect='refuse'
 return im,boxes,expect
if __name__=='__main__':
 if (B/'FIXTURE-RESULT.json').exists():raise SystemExit('No repeated frozen fixture run')
 rows=[];start=time.monotonic()
 for kind in ['wide_white_background','white_overpaint','late_separate_text','transparent_overlay','touching_distinct_objects','unseeded_dot']:
  im,boxes,expected=fixture(kind);owners,r=partition(np.asarray(im),boxes);r.update({'case':kind,'expected':expected,'expectation_met':r['whole_page_refusal']==(expected=='refuse')});rows.append(r);im.save(B/'evidence'/(kind+'.png'))
 out={'rows':rows,'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'source_sha256':hashlib.sha256((B/'code/masks.py').read_bytes()).hexdigest(),'scope':'Original oracle-semantic-seed invariant test, not real candidate or reading-order evidence.'};(B/'FIXTURE-RESULT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
