"""Original self-contained image reader. Exports no document text or network URLs."""
import pathlib,json,base64,io
from PIL import Image

def data(image):
 b=io.BytesIO();image.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
def export_page(root,key,page):
 root=pathlib.Path(root);r=json.loads((root/'output'/(key+'-result.json')).read_text());source=Image.open(root/'inputs'/(key+'.png')).convert('RGB');canvas=Image.open(root/'evidence'/(key+'-column.png')).convert('RGB');pieces=[]
 for n in r['nodes']:
  a,b,c,d=n['bbox'];tw,th=n['target_size'];y=n['target_y'];display=canvas.crop((0,y,tw,y+th))
  pieces.append({'display':data(display),'source':data(source.crop((a,b,c,d))),'bbox':[a,b,c,d],'width':tw,'height':th,'protected':n['mode']!='candidate_word_reflow'})
 return {'page':page,'source':data(source),'refused':bool(r['failure']),'reason':'未能确认完整结构，保留整页' if r['failure'] else '', 'pieces':pieces}
def write_reader(pages,path):
 payload=json.dumps(pages,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c');template=pathlib.Path(__file__).with_name('reader.html').read_text();assert template.count('__PAGES_JSON__')==1;pathlib.Path(path).write_text(template.replace('__PAGES_JSON__',payload))
