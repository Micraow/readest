"""Local CSS layout snapshots and positions; explicitly not browser validation."""
import os,pathlib,argparse,time,json,re
p=argparse.ArgumentParser();p.add_argument('html');p.add_argument('out');p.add_argument('--width',type=int,default=390);p.add_argument('--font',type=int,default=20);a=p.parse_args();B=pathlib.Path(a.out);B.mkdir(parents=True,exist_ok=True);os.environ['XDG_CACHE_HOME']=str(B/'font-cache');(B/'font-cache').mkdir(exist_ok=True)
from weasyprint import HTML
import fitz
from PIL import Image
start=time.monotonic();text=pathlib.Path(a.html).read_text();text=re.sub(r'<script[^>]*>[\s\S]*?</script>','',text);text=re.sub(r'<dialog[\s\S]*?</dialog>','',text)
css=f'@page{{size:{a.width}px 12000px;margin:0}}body{{--reader-width:{a.width}px!important;--reader-font:{a.font}px!important;background:white}}.shell{{width:{a.width}px;max-width:none;min-height:0}}header,.notice,dialog{{display:none}}.object,.wide-local{{overflow:hidden}}'
text=text.replace('</style>','</style><style>'+css+'</style>',1);doc=HTML(string=text).render();pdf=doc.write_pdf();positions=[]
for pg,page in enumerate(doc.pages):
 for box in page._page_box.descendants():
  el=getattr(box,'element',None)
  if el is not None and el.get('data-unit') and type(box).__name__ in {'InlineBlockBox','BlockBox'}:positions.append({'id':el.get('data-unit'),'page':pg,'x':box.position_x,'y':box.position_y,'width':box.width,'height':box.height,'font_size':box.style['font_size']})
pages=fitz.open(stream=pdf,filetype='pdf');images=[]
for page in pages:
 pix=page.get_pixmap(matrix=fitz.Matrix(4/3,4/3),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);bb=im.convert('L').point(lambda v:255 if v<250 else 0).getbbox();im=im.crop((0,0,im.width,min(im.height,bb[3]+18 if bb else 1)));images.append(im)
canvas=Image.new('RGB',(a.width,sum(i.height for i in images)),'white');y=0
for im in images:canvas.paste(im,(0,y));y+=im.height
canvas.save(B/f'{a.width}-{a.font}.png');(B/f'{a.width}-{a.font}-positions.json').write_text(json.dumps({'scope':'WeasyPrint layout, not Chromium','width':a.width,'font':a.font,'units':positions,'seconds':time.monotonic()-start,'image_size':list(canvas.size)},indent=2));print(json.dumps({'units':len(positions),'image_size':list(canvas.size),'seconds':time.monotonic()-start}))
