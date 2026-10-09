"""Original PDF stencil-image controls; no third-party page or learned labels."""
import pathlib,json,hashlib,sys,os,resource
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
import fitz,numpy as np
from PIL import Image,ImageDraw
from envelope import inspect
B=pathlib.Path(__file__).resolve().parents[1]
def pdf(content,rotation,decode):
 objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 240] /Rotate {rotation} /Resources << /XObject << /Mask 5 0 R >> >> /Contents 4 0 R >>'.encode(),f'<< /Length {len(content)} >>\nstream\n'.encode()+content+b'\nendstream',f'<< /Type /XObject /Subtype /Image /Width 8 /Height 8 /ImageMask true /BitsPerComponent 1 /Decode [{decode}] /Length 8 >>\nstream\n'.encode()+bytes([0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81])+b'\nendstream']
 out=b'%PDF-1.4\n';offsets=[0]
 for i,o in enumerate(objects,1):offsets.append(len(out));out+=f'{i} 0 obj\n'.encode()+o+b'\nendobj\n'
 x=len(out);out+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()+b''.join(f'{v:010d} 00000 n \n'.encode() for v in offsets[1:]);out+=f'trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode();return out
cases=[('black',b'q 0 g 120 0 0 120 50 55 cm /Mask Do Q',0,'0 1',None),('red',b'q 1 0 0 rg 120 0 0 120 50 55 cm /Mask Do Q',0,'0 1',None),('rotated',b'q 0 g 120 0 0 120 50 55 cm /Mask Do Q',90,'0 1',None),('inverse',b'q 0 g 120 0 0 120 50 55 cm /Mask Do Q',0,'1 0',None),('white-overpaint',b'q 0 g 120 0 0 120 50 55 cm /Mask Do Q 1 g 45 50 135 135 re f',0,'0 1',None),('clipped-origin',b'q 0 g 120 0 0 120 50 55 cm /Mask Do Q',0,'0 1',(90,90,190,190))]
rows=[];sheet=Image.new('RGB',(900,600),'#ddd');dr=ImageDraw.Draw(sheet)
for i,(name,content,rot,decode,clip) in enumerate(cases):
 data=pdf(content,rot,decode);p=fitz.open(stream=data,filetype='pdf')[0];pix,check=inspect(p,4,clip=fitz.Rect(clip) if clip else None);types=[t[0] for t in p.get_bboxlog()];assert 'fill-imgmask' in types;assert check['outside_physical_paint_envelopes']==0 and check['changed_rgb_pixels_after_guard']==0
 image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);image.thumbnail((285,265));sheet.paste(image,(i%3*300,i//3*300+30));dr.text((i%3*300+8,i//3*300+6),name,fill='black');(B/'evidence'/f'{name}.pdf').write_bytes(data)
 rows.append({'case':name,'pdf_sha256':hashlib.sha256(data).hexdigest(),'native_paint_types':types,'source_ink':check['source_ink'],'outside_physical_paint_envelopes':check['outside_physical_paint_envelopes'],'changed_rgb_pixels':check['changed_rgb_pixels_after_guard']})
sheet.save(B/'evidence/controls.png');(B/'CONTROLS.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
