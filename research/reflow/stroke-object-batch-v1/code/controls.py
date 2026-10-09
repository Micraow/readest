"""Original geometry controls for visible stroke retention, not paper fixtures."""
import fitz,numpy as np,json,pathlib
from primitives import divider_seeds
B=pathlib.Path(__file__).resolve().parents[1]
rows=[]
for name,kind,expected in [('black_between_body','black',1),('white_fill_background','white',0),('vertical','vertical',0),('ambiguous_two_strokes','double',0),('overlapping_semantic_parent','overlap',0)]:
 d=fitz.open();p=d.new_page(width=220,height=160)
 if kind=='white':p.draw_rect(fitz.Rect(10,60,210,64),fill=(1,1,1),color=None)
 else:
  for _ in range(2 if kind=='double' else 1):p.draw_line(fitz.Point(20,70),fitz.Point(20,140) if kind=='vertical' else fitz.Point(200,70),color=(0,0,0),width=.4)
 pix=p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False);a=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3);nodes=[{'bbox':[30,110,420,160] if kind=='overlap' else [30,175,420,220],'labels':['text'],'evidence':['authored'],'forced_original':False}];events=divider_seeds(p,pix,2,a,nodes,20,None);rows.append({'case':name,'expected_recovered':expected,'recovered':len(events)})
(B/'CONTROLS.json').write_text(json.dumps(rows,indent=2));print(rows);assert all(x['expected_recovered']==x['recovered'] for x in rows)
