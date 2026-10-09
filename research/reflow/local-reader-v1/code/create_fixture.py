"""Original content only. One native PDF page and its raster-only counterpart."""
import pathlib,io,textwrap
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader
import fitz
from PIL import Image
B=pathlib.Path(__file__).resolve().parents[1];out=B/'fixtures/original-reader-fixture.pdf';buffer=io.BytesIO();c=Canvas(buffer,pagesize=(480,640),invariant=1)
c.setFont('Helvetica-Bold',17);c.drawString(40,595,'A small study of local reading')
c.setFont('Times-Roman',11);y=558
paragraphs=['A local reader should keep the original marks while adapting ordinary paragraphs to a narrow display. This example contains only text and shapes written for the experiment. The page is a test input, and it is not evidence that unseen scientific papers will be reconstructed correctly.','Some objects need their original arrangement. A reader can retain an equation as one image and let the person inspect it at a useful size. This preserves the printed symbols while leaving mathematical line breaking as an unresolved task.']
for para in paragraphs:
 for line in textwrap.wrap(para,85):c.drawString(40,y,line);y-=15
 y-=14
c.setFont('Times-Italic',14);c.drawCentredString(230,y-3,'a + b = c');c.setFont('Times-Roman',11);c.drawString(405,y-3,'(1)');y-=42
c.setFillColorRGB(.18,.45,.73);c.rect(65,y-65,130,65,fill=1,stroke=0);c.setFillColorRGB(.85,.4,.2);c.rect(230,y-40,130,40,fill=1,stroke=0);c.setFillColorRGB(0,0,0);c.setFont('Times-Roman',10);c.drawString(65,y-80,'Figure 1. Blue and orange bars remain distinct.')
y-=115;c.setFont('Times-Roman',11)
for line in textwrap.wrap('The final paragraph follows the figure. Its order, content and actual word wrapping can be checked against the original page. Opening a large source image is useful, but that action must not be counted as successful automatic text reflow.',85):c.drawString(40,y,line);y-=15
c.setFont('Times-Roman',9);c.drawCentredString(240,28,'1');c.save();original=fitz.open(stream=buffer.getvalue(),filetype='pdf');pix=original[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);image.save(B/'fixtures/source-preview.png');target=fitz.open();target.insert_pdf(original);page=target.new_page(width=480,height=640);imagebytes=io.BytesIO();image.save(imagebytes,format='PNG');page.insert_image(page.rect,stream=imagebytes.getvalue());target.save(out);print(out)
