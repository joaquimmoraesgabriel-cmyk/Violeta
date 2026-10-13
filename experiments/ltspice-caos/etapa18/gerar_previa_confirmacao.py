"""Trecho inicial real: pode ser inspecionado antes do termino da matriz."""
from pathlib import Path
import csv,io,math,re
import numpy as np
from reportlab.graphics.shapes import Drawing,String,Rect,Line,PolyLine
from reportlab.graphics import renderSVG,renderPDF
from reportlab.lib.colors import HexColor
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parent
data=[];export=[]
for name in ['L2_5_10','L2_5_10_v2']:
    p=ROOT/f'{name}.raw'
    with p.open('rb') as f:prefix=f.read(32768)
    marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker);assert pos>=0
    names=[n.lower() for n in re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)]
    dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);off=pos+len(marker)
    rec=np.memmap(p,mode='r',offset=off,dtype=dtype,shape=(min(50000,(p.stat().st_size-off)//dtype.itemsize),))
    c={n:rec['v'][:,i] for i,n in enumerate(names[1:])};t=rec['time'];assert t[0]==0 and t[-1]>.0024
    m=(t>=.0021)&(t<=.0024)
    vals=(t[m]*1e6,c['v(erro_cota)'][m].astype(float)*1e6,c['v(timer_cota)'][m].astype(float),c['v(reserva_cota)'][m].astype(float))
    data.append(vals)
    export += [dict(modelo=name,tempo_us=a,erro_uA=b,timer=cc,reserva=dd) for a,b,cc,dd in zip(*vals)]
with (ROOT/'trecho_confirmacao.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(export[0]));w.writeheader();w.writerows(export)
d=Drawing(980,640);d.add(Rect(0,0,980,640,fillColor=HexColor('#F7F9FB'),strokeColor=None))
def text(x,y,s,size=12,color='#182C3C',bold=False):
    d.add(String(x,y,s,fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,fillColor=HexColor(color)))
text(30,605,'Diagnóstico: um alarme com capacidade sobrando',22,bold=True)
text(30,579,'L2 5/10 µs saudável: trecho inicial do primeiro percurso, passo máximo 1,25 µs.',12)
colors=['#A55650','#197A85']
emax=max(4,4*math.ceil(max(v[1].max() for v in data)/4))
for panel,(title,col,maximum,threshold) in enumerate([('Discrepância das cotas (µA)',1,emax,6.5),('Estado da confirmação RC',2,1,.7)]):
    x0=75;y0=340 if panel==0 else 115;w=850;h=165
    text(x0,y0+h+20,title,14,bold=True)
    for v in np.linspace(0,maximum,5):
        yy=y0+h*v/maximum;d.add(Line(x0,yy,x0+w,yy,strokeColor=HexColor('#DDE5EC'),strokeWidth=.5));text(35,yy-3,f'{v:g}',10)
    yy=y0+h*threshold/maximum;d.add(Line(x0,yy,x0+w,yy,strokeColor=HexColor('#404E5C'),strokeDashArray=[4,3],strokeWidth=1))
    for values,color in zip(data,colors):
        points=np.column_stack([x0+w*(values[0]-2100)/300,y0+h*values[col]/maximum]).ravel().tolist()
        d.add(PolyLine(points,strokeColor=HexColor(color),strokeWidth=1.3,fillColor=None))
    for v in [2100,2200,2300,2400]:text(x0+w*(v-2100)/300-12,y0-17,str(v),10)
text(720,75,'Tempo desde a partida (µs)',11)
text(75,53,'V1: carga/descarga 20/40 µs',11,colors[0]);text(390,53,'V2: carga/descarga 50/20 µs',11,colors[1])
text(75,31,'Linhas tracejadas: limiares. Este trecho explica o disparo inicial; a matriz completa continua em execução.',10)
renderSVG.drawToFile(d,str(ROOT/'previa_confirmacao.svg'))
buf=io.BytesIO();renderPDF.drawToFile(d,buf);pdf=pdfium.PdfDocument(buf.getvalue());page=pdf[0]
bitmap=page.render(scale=1.5);bitmap.to_pil().save(ROOT/'previa_confirmacao.png');bitmap.close();page.close();pdf.close()
print('Previa criada a partir do RAW real; CSV do trecho preservado.')
