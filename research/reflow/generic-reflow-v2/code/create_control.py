"""One original mechanism control; not a generalization corpus."""
from reportlab.pdfgen import canvas
from pathlib import Path
import sys
p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
c=canvas.Canvas(str(p),pagesize=(420,500),invariant=1)
c.setFillColorRGB(.87,.87,.87);c.rect(35,255,350,195,fill=1,stroke=0)
c.setFillColorRGB(0,0,0);c.setFont('Helvetica',12)
for i,t in enumerate(['A shaded panel should remain ordinary readable text.', 'Its background is a separate painted object.', 'Narrow screens should wrap these words naturally.', 'The following equation must retain its fraction bar.']):c.drawString(45,425-i*23,t)
c.setFont('Times-Roman',12);c.drawString(130,301,'x + y');c.drawString(139,280,'2');c.line(126,296,164,296);c.drawString(169,292,'= z')
c.setFont('Helvetica',12);c.drawString(40,218,'Table borders below must remain foreground paint.')
for x in [40,210,380]:c.line(x,115,x,195)
for y in [115,155,195]:c.line(40,y,380,y)
for x,y,t in [(50,170,'Alpha'),(220,170,'One'),(50,130,'Beta'),(220,130,'Two')]:c.drawString(x,y,t)
c.save()
