import pathlib,json,sys
import fitz,numpy as np
from roles import label_candidate,external_label_supported
from primitives import divider_seeds
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'paint-envelope-v1/code'))
from envelope import raster_box
B=pathlib.Path(__file__).resolve().parents[1];rows=[]
for name,kind,expected in [('horizontal_footnote','line',True),('white_background','fill',False),('vertical_stroke','vertical',False),('line_above_prose','prose',False)]:
 d=fitz.open();p=d.new_page(width=240,height=220)
 if kind=='fill':p.draw_rect(fitz.Rect(0,80,240,200),fill=(1,1,1),color=None)
 elif kind=='vertical':p.draw_line((30,75),(30,130),width=.4)
 else:p.draw_line((30,130),(160,130),width=.4)
 p.insert_text((30,145),'A source note below.',fontsize=10);pix=p.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False);rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3);bb=raster_box(p.get_text('blocks')[0][:4],p,pix,4);nodes=[{'bbox':bb,'labels':['text' if kind=='prose' else 'footnote'],'evidence':[]}];events=divider_seeds(p,pix,4,rgb,nodes,40,raster_box);rows.append({'case':name,'expected':expected,'accepted':bool(events)})
labels={x:label_candidate(x) for x in ['(2.4)','[A.1]','(iii)','(*)','3','1/N','(x+y)','3.2. Heading']}
assert all(x['expected']==x['accepted'] for x in rows)
assert all(labels[x] for x in ['(2.4)','[A.1]','(iii)','(*)','3']) and not any(labels[x] for x in ['1/N','(x+y)','3.2. Heading'])
(B/'CONTROLS.json').write_text(json.dumps({'native_primitives':rows,'identifier_schema':labels},indent=2));print(rows,labels)
