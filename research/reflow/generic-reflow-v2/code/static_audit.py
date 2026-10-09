"""WeasyPrint static-only visual diagnostic. Never browser-interaction evidence."""
import argparse,json,pathlib,time
from weasyprint import HTML,CSS
import pypdfium2 as pdfium

def run(folder,width=390,size=20):
 p=pathlib.Path(folder);start=time.perf_counter();doc=HTML(filename=str(p/'reader.html')).render(stylesheets=[CSS(string=f'@page{{size:{width}px 6000px;margin:0}} body{{width:{width}px;font-size:{size}px}} main{{font-size:{size}px !important}} nav{{display:none}}')]);doc.write_pdf(p/f'static-{width}-{size}.pdf')
 pdf=pdfium.PdfDocument(p/f'static-{width}-{size}.pdf');image=pdf[0].render(scale=1).to_pil();image.save(p/f'static-{width}-{size}.png')
 boxes=[]
 def walk(b):
  el=getattr(b,'element',None)
  if el is not None and el.get('data-atom') and type(b).__name__=='BlockBox':boxes.append(dict(id=el.get('data-atom'),x=b.position_x,y=b.position_y,width=b.width,height=b.height))
  for c in b.all_children():walk(c)
 for page in doc.pages:walk(page._page_box)
 for b in boxes:
  bounds=(max(0,int(b['x']*.75)-6),max(0,int(b['y']*.75)-6),min(image.width,int((b['x']+b['width']+25)*.75)),min(image.height,int((b['y']+b['height']+25)*.75)))
  image.crop(bounds).save(p/f'static-panel-{width}-{size}-{b["id"]}.png')
 result=dict(renderer='WeasyPrint, not Chromium or Android',width=width,font=size,pages=len(doc.pages),seconds=time.perf_counter()-start,background_boxes=boxes,interaction_verified=False)
 (p/f'static-{width}-{size}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--width',type=int,default=390);p.add_argument('--size',type=int,default=20);a=p.parse_args();run(a.folder,a.width,a.size)
