"""Grafico SVG com curvas reais exportadas pelo LTspice."""
from pathlib import Path
import re
import numpy as np
from reportlab.graphics.shapes import Drawing, String, Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
data=(ROOT/'MLC_AND_pilar_demo_v2.raw').read_bytes()
marker='Binary:\n'.encode('utf-16-le')
offset=data.find(marker)
if offset<0:
    marker='Binary:\r\n'.encode('utf-16-le')
    offset=data.find(marker)
if offset<0:
    raise RuntimeError('Cabecalho binario LTspice ausente.')
header=data[:offset].decode('utf-16-le')
count=int(re.search(r'No. Variables:\s*(\d+)',header).group(1))
points=int(re.search(r'No. Points:\s*(\d+)',header).group(1))
variables=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',header,re.M)
if 'FastAccess' in header or 'double' in header:
    raise RuntimeError('Formato RAW nao suportado por este grafico.')
record=np.dtype([('time','<f8'),('values','<f4',(count-1,))])
records=np.frombuffer(data,offset=offset+len(marker),dtype=record,count=points)
time=records['time']
cuts=np.flatnonzero(np.diff(time)<0)+1
parts=np.split(records,cuts)
if len(parts)!=2:
    raise RuntimeError('Esperadas duas execucoes: controle=0 e controle=1.')
x_index=variables.index('V(x)')-1

drawing=Drawing(1000,510)
drawing.add(String(55,480,'Porta AND: mesmo desvio, com e sem o pilar',fontName='Helvetica-Bold',fontSize=18))
drawing.add(String(55,459,'Modelo ideal MLC; amortecimento +0,5%; referencia +0,02%. Curvas reais do LTspice.',fontSize=10))
for plot_index,(part,label,color) in enumerate(zip(parts,('Pilar desligado','Pilar ligado'),(colors.HexColor('#a14425'),colors.HexColor('#176750')))):
    mask=(part['time']>=0.50)&(part['time']<=0.65)
    section=part[mask][::5]
    plot=LinePlot()
    plot.x,plot.y,plot.width,plot.height=70,270-plot_index*210,875,140
    plot.data=[list(zip(section['time']*1000,section['values'][:,x_index]))]
    plot.xValueAxis.valueMin,plot.xValueAxis.valueMax=500,650
    plot.xValueAxis.valueSteps=list(range(500,651,25))
    plot.yValueAxis.valueMin,plot.yValueAxis.valueMax=-1.6,1.6
    plot.yValueAxis.valueSteps=[-1,0,1]
    plot.lines[0].strokeColor=color
    plot.lines[0].strokeWidth=0.7
    plot.xValueAxis.labels.fontSize=9
    plot.yValueAxis.labels.fontSize=9
    drawing.add(plot)
    drawing.add(Line(70,plot.y+70,945,plot.y+70,strokeColor=colors.HexColor('#999999'),strokeWidth=0.5))
    drawing.add(String(70,plot.y+157,label,fontName='Helvetica-Bold',fontSize=12,fillColor=color))
    drawing.add(String(80,plot.y+143,'A,B = 0,1',fontSize=9))
    drawing.add(String(370,plot.y+143,'A,B = 1,1',fontSize=9))
    drawing.add(String(665,plot.y+143,'A,B = 1,0',fontSize=9))
    drawing.add(String(22,plot.y+70,'x',fontSize=11))
drawing.add(String(450,25,'Tempo (ms)',fontSize=11))
drawing.add(String(70,8,'Leitura: x > 0 representa 1; x < 0 representa 0. Transicoes possuem tempo de acomodacao.',fontSize=9))
renderSVG.drawToFile(drawing,str(ROOT/'MLC_comparacao.svg'))
print('MLC_comparacao.svg criado com '+str(points)+' pontos reais, reduzidos apenas para visualizacao.')
