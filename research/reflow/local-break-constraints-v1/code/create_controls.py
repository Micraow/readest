"""Original authored controls; coordinates/relations are used only by QA."""
import pathlib,io,json,hashlib
import fitz
from reportlab.pdfgen.canvas import Canvas
B=pathlib.Path(__file__).resolve().parents[1];D=B/'controls';D.mkdir(exist_ok=True)
b=io.BytesIO();c=Canvas(b,pagesize=(480,640),invariant=1);c.setFont('Times-Roman',11)
lines=['A compact reader should keep every original printed mark.', 'Only uncertain local relationships should remain together.', 'A local expression                      should remain in its place.', 'lines when the reading width changes on a small screen.']
for i,line in enumerate(lines):c.drawString(40,580-i*16,line)
# Authored script placement straddles plausible neighboring bases in a text block.
c.setFont('Times-Italic',11);c.drawString(150,548,'x');c.setFont('Times-Roman',7);c.drawString(156,552,'2');c.drawString(157,544,'i')
c.setFont('Times-Roman',11);c.drawString(40,470,'An equation follows, with a separate identifying number.')
c.setFont('Times-Italic',12);c.drawString(205,425,'x + y');c.line(196,420,248,420);c.drawString(205,405,'a + b');c.setFont('Times-Roman',11);c.drawString(416,418,'(2)')
c.setFont('Times-Roman',11);c.drawString(40,370,'A matrix keeps its rows, columns and enclosing brackets.')
c.setFont('Times-Italic',12)
for x,y,t in [(190,330,'a'),(225,330,'b'),(190,308,'c'),(225,308,'d')]:c.drawString(x,y,t)
for x,side in [(177,1),(244,-1)]:c.line(x,302,x,342);c.line(x,302,x+side*7,302);c.line(x,342,x+side*7,342)
c.setFont('Times-Roman',11);c.drawString(40,265,'A later ordinary sentence must continue after the matrix.')
t=c.beginText(40,222);t.setFont('Times-Roman',11);t.setTextRenderMode(2);t.textOut('Repeated fill and stroke paint must not duplicate a word.');c.drawText(t)
c.setFont('Times-Roman',11);c.drawString(40,175,'A following clean paragraph should remain fully movable.')
c.save();doc=fitz.open(stream=b.getvalue(),filetype='pdf');doc.save(D/'geometry.pdf')
# Native ligature and CJK text, with explicit supported built-in font sources.
d=fitz.open();p=d.new_page(width=480,height=480);font=fitz.Font('cjk');tw=fitz.TextWriter(p.rect)
for i,text in enumerate(['局部关系存在歧义时，只保留附近原子的相对位置。','其余正文应当按照手机屏幕宽度自动换行，不能缩成小图。','图表和数学表达式可以局部查看，原页仅作为可选对照。']):tw.append((35,70+i*23),text,font=font,fontsize=11)
tw.write_text(p);font2=fitz.Font('Times-Roman');tw=fitz.TextWriter(p.rect);tw.append((35,180),'Office words and ligature forms must keep their marks.',font=font2,fontsize=11);tw.write_text(p);d.save(D/'cjk.pdf')

# Genuine Unicode ligature glyphs, using an already-installed font; no font download.
d=fitz.open();p=d.new_page(width=400,height=260);font=fitz.Font(fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf');tw=fitz.TextWriter(p.rect)
for i,text in enumerate(['Native ligatures stay visible: ofﬁce and oﬃce.','Changing width must not paint a ligature twice.']):tw.append((25,65+i*20),text,font=font,fontsize=11)
tw.write_text(p);d.save(D/'ligature.pdf')

manifest={'scope':'Original development controls only, never new-paper evidence','pdfs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in D.glob('*.pdf')},'expected_relations':['script2 and i stay with authored local x geometry; neighboring body not globally refused','fraction numerator/bar/denominator preserved as a local object','matrix all four cells and both brackets remain spatially coherent','equation2 association without locking blank gap','fill/stroke does not duplicate visible source word','CJK ordinary glyphs can rewrap without treating a whole native line as one unbreakable word']};(D/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
