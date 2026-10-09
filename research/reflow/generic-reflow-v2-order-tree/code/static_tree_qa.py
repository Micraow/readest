"""Actual moved/scaled static layout inspection, explicitly not browser evidence."""
import argparse,hashlib,json,pathlib,time
from weasyprint import HTML,CSS
import pypdfium2 as pdfium
from PIL import Image

def run(folder,source='tree-reader.html',widths=(320,390,430),sizes=(20,28)):
 folder=pathlib.Path(folder);assets=json.loads((folder/'tree-reader-assets-private.json').read_text());mapping={a['id']:a for a in assets['results']};out=folder/'static-qa';out.mkdir(exist_ok=True);results=[];start=time.perf_counter()
 for width in widths:
  for size in sizes:
   doc=HTML(filename=str(folder/source)).render(stylesheets=[CSS(string=f'@page{{size:{width}px 12000px;margin:0}}body{{width:{width}px;font-size:{size}px!important}}main{{font-size:{size}px!important}}nav{{display:none}}')]);pdfname=f'{width}-{size}.pdf';doc.write_pdf(out/pdfname);boxes=[];background=[]
   def walk(b):
    el=getattr(b,'element',None)
    if el is not None:
     if el.get('data-unit') and type(b).__name__ in {'InlineBlockBox','InlineReplacedBox'}:boxes.append(dict(id=el.get('data-unit'),type=type(b).__name__,x=b.position_x,y=b.position_y,width=b.width,height=b.height,font_size=b.style['font_size']))
     if el.get('data-background') and type(b).__name__=='BlockBox':background.append(dict(id=el.get('data-background'),x=b.position_x,y=b.position_y,width=b.width,height=b.height))
    for c in b.all_children():walk(c)
   for page in doc.pages:walk(page._page_box)
   checks=[]
   for box in boxes:
    asset=mapping[box['id']]
    if asset['kind'] not in {'native_word','inline_native_group'}:continue
    expected=(asset['width_em']*box['font_size'],asset['height_em']*box['font_size'])
    checks.append(dict(id=box['id'],expected=list(expected),actual=[box['width'],box['height']],affine_geometry_pass=abs(box['width']-expected[0])<1e-6 and abs(box['height']-expected[1])<1e-6))
   pdf=pdfium.PdfDocument(out/pdfname);image=pdf[0].render(scale=1).to_pil();image.save(out/f'{width}-{size}.png')
   image.crop((0,0,image.width,min(image.height,900))).save(out/f'{width}-{size}-top.png')
   for bg in background:
    x0=max(0,int(bg['x']*.75)-4);y0=max(0,int(bg['y']*.75)-4);x1=min(image.width,int((bg['x']+bg['width']+30)*.75));y1=min(image.height,int((bg['y']+bg['height']+30)*.75));image.crop((x0,y0,x1,y1)).save(out/f'{width}-{size}-panel-{bg["id"]}.png')
   pdf.close();ids=[b['id'] for b in boxes];results.append(dict(width=width,font_size=size,pages=len(doc.pages),unit_boxes=boxes,affine_checks=checks,duplicate_unit_boxes=len(ids)!=len(set(ids)),all_affine_geometry_pass=all(c['affine_geometry_pass'] for c in checks),background_boxes=background))
 result=dict(renderer='WeasyPrint static PDF, not Chromium/Android',source=source,seconds=time.perf_counter()-start,settings=results,asset_sha256={a['id']:hashlib.sha256((folder/a['file']).read_bytes()).hexdigest() for a in assets['results'] if not a.get('empty')},claims=['source asset reused once per emitted unit','local relative geometry scales affinely where checked'],not_verified=['semantic paragraph and global reading order','live browser selection','live local zoom','new raster quality when increasing font size beyond the source sampling density'])
 (out/'static-layout-audit-private.json').write_text(json.dumps(result,indent=2));print(json.dumps({'settings':len(results),'all_affine_pass':all(r['all_affine_geometry_pass'] for r in results),'duplicates':any(r['duplicate_unit_boxes'] for r in results),'seconds':result['seconds']}));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--source',default='tree-reader.html');p.add_argument('--one-width',type=int);a=p.parse_args();run(a.folder,a.source,(a.one_width,) if a.one_width else (320,390,430))
