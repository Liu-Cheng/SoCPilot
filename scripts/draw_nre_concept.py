"""Generate the qualitative NRE break-even diagram. Requires reportlab.
Run from any directory: python scripts/draw_nre_concept.py
Parameters are illustrative dimensionless values, not measured cost data.
"""
from pathlib import Path
from math import log10
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
out=Path(__file__).resolve().parents[1]/'pic'/'nre-break-even.pdf'
c=canvas.Canvas(str(out),pagesize=(380,238))
c.setTitle('Qualitative effect of NRE reduction on ASIC break-even volume')
blue=HexColor('#245B91'); green=HexColor('#147D73'); gray=HexColor('#59636F')
x0,x1,y0,y1=53,363,53,215
xmin,xmax=.4,30
YMAX=5
X=lambda q:x0+(log10(q)-log10(xmin))/(log10(xmax)-log10(xmin))*(x1-x0)
Y=lambda v:y0+v/YMAX*(y1-y0)
base=2.6; unit=.65;nold=8;nnew=2.8
qold=nold/(base-unit);qnew=nnew/(base-unit)
c.setFillColor(HexColor('#E6F2EE'));c.rect(X(qnew),y0,X(qold)-X(qnew),y1-y0,stroke=0,fill=1)
def text(x,y,s,size=10,color=gray,font='Helvetica'):
 c.setFillColor(color);c.setFont(font,size);c.drawString(x,y,s)
def line(xa,ya,xb,yb,color,width=1,dash=None):
 c.setStrokeColor(color);c.setLineWidth(width);c.setDash(dash or []);c.line(xa,ya,xb,yb);c.setDash([])
def arrow(xa,ya,xb,yb,color,width=1,head=5):
 line(xa,ya,xb,yb,color,width)
 dx,dy=xb-xa,yb-ya
 length=(dx*dx+dy*dy)**.5
 ux,uy=dx/length,dy/length
 p=c.beginPath();p.moveTo(xb,yb)
 p.lineTo(xb-head*ux+head*.45*uy,yb-head*uy-head*.45*ux)
 p.lineTo(xb-head*ux-head*.45*uy,yb-head*uy+head*.45*ux)
 p.close();c.setFillColor(color);c.drawPath(p,stroke=0,fill=1)
arrow(x0,y0,x1+7,y0,gray);arrow(x0,y0,x0,y1+9,gray)
line(x0,Y(base),x1,Y(base),gray,1,[4,3])
for n,col in [(nold,blue),(nnew,green)]:
 path=c.beginPath(); started=False
 for i in range(501):
  q=10**(log10(xmin)+(log10(xmax)-log10(xmin))*i/500); v=unit+n/q
  if v>YMAX: continue
  if not started:path.moveTo(X(q),Y(v));started=True
  else:path.lineTo(X(q),Y(v))
 c.setStrokeColor(col);c.setLineWidth(2);c.drawPath(path)
for q,col,lab in [(qnew,green,'Q* LLM'),(qold,blue,'Q* conventional')]:
 line(X(q),y0,X(q),Y(base),col,1,[2,2]);c.setFillColor(col);c.circle(X(q),Y(base),3,stroke=0,fill=1)
 c.setFont('Helvetica',9);c.drawCentredString(X(q),y0-13,lab)
text(231,Y(base)+7,'Off-the-shelf alternative',9)
text(242,118,'Conventional ASIC',10,blue)
text(242,65,'LLM-assisted ASIC',10,green)
# Leftward arrow connects break-even volumes in the newly viable region.
ay=Y(base)-22
line(X(qold)-3,ay,X(qnew)+3,ay,green,1.5)
p=c.beginPath();p.moveTo(X(qnew)+3,ay);p.lineTo(X(qnew)+10,ay+3);p.lineTo(X(qnew)+10,ay-3);p.close();c.setFillColor(green);c.drawPath(p,stroke=0,fill=1)
text(225,196,'Lower NRE',10,green,'Helvetica-Bold')
text(225,183,'moves break-even left',9,green)
c.saveState();c.translate(25,(y0+y1)/2);c.rotate(90)
c.setFillColor(gray);c.setFont('Helvetica',10);c.drawCentredString(0,0,'Average total cost per unit');c.restoreState()
c.setFillColor(gray);c.setFont('Helvetica',10);c.drawCentredString(208,21,'Production volume Q')
c.save()
print(out)
