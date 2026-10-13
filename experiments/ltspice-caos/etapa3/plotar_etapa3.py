"""Compara curvas reais LTspice numa janela que falhou sem o pilar."""
from pathlib import Path
import json
import re
import numpy as np
from reportlab.graphics.shapes import Drawing,String,Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
summary=json.loads((ROOT/'resumo_etapa3.json').read_text(encoding='utf-8'))
off=next(item for item in summary if item['arquivo']=='MLC_dinamico_demo.log' and item['modo']=='desligado')
window=off['falhas'][0]['janela'] if off['falhas'] else 6
start,end=window*0.05+0.030,(window+1)*0.05-0.001
code=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0][window]
data=(ROOT/'MLC_dinamico_demo.raw').read_bytes()
marker='Binary:\n'.encode('utf-16-le')
offset=data.find(marker)
if offset<0:
    marker='Binary:\r\n'.encode('utf-16-le'); offset=data.find(marker)
if offset<0:
    raise RuntimeError('Formato RAW nao reconhecido.')
header=data[:offset].decode('utf-16-le')
nvars=int(re.search(r'No. Variables:\s*(\d+)',header).group(1))
npoints=int(re.search(r'No. Points:\s*(\d+)',header).group(1))
names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',header,re.M)
records=np.frombuffer(data,offset=offset+len(marker),dtype=np.dtype([('time','<f8'),('values','<f4',(nvars-1,))]),count=npoints)
parts=np.split(records,np.flatnonzero(np.diff(records['time'])<0)+1)
if len(parts)!=4:
    raise RuntimeError('Esperados quatro modos na demonstracao.')


def curve(mode,name,scale=1):
    part=parts[mode]
    section=part[(part['time']>=start)&(part['time']<=end)][::2]
    return list(zip(section['time']*1000,section['values'][:,names.index(name)-1]*scale))


drawing=Drawing(1000,790)
drawing.add(String(65,760,'Pilar com atraso e corrente limitada',fontName='Helvetica-Bold',fontSize=18))
drawing.add(String(65,740,f'Curvas LTspice: janela {window}; A={code//2}, B={code%2}; AND esperada={int(code==3)}. Referencia com erro de +0,02%.',fontSize=10))
red=colors.HexColor('#af482b'); green=colors.HexColor('#146d60'); blue=colors.HexColor('#346ea3')
plots=[
    ('Mudanca real e ajuste atrasado (%)',[curve(2,'V(perturbacao)',100),curve(2,'V(ajuste)',100)],['Perturbacao','Ajuste do pilar'],[red,green],(-0.6,0.6)),
    ('Estado x: a leitura deve permanecer no lado correto de zero',[curve(0,'V(x)'),curve(2,'V(x)')],['Pilar desligado','Pilar limitado'],[red,green],(-1.6,1.6)),
    ('Corrente aplicada pelo pilar (microampere)',[curve(2,'I(Bcorrecao)',1e6),curve(3,'I(Bcorrecao)',1e6)],['Limite +/-100 uA','Limite +/-20 uA'],[green,blue],(-100,100)),
]
for index,(title,data_curves,labels,palette,limits) in enumerate(plots):
    y=540-index*230
    plot=LinePlot(); plot.x=75; plot.y=y; plot.width=875; plot.height=155
    plot.data=data_curves
    plot.xValueAxis.valueMin=start*1000; plot.xValueAxis.valueMax=end*1000
    plot.yValueAxis.valueMin=limits[0]; plot.yValueAxis.valueMax=limits[1]
    plot.yValueAxis.valueSteps=[limits[0],0,limits[1]]
    plot.xValueAxis.labels.fontSize=9; plot.yValueAxis.labels.fontSize=9
    for number,color in enumerate(palette):
        plot.lines[number].strokeColor=color; plot.lines[number].strokeWidth=0.8
    drawing.add(plot)
    drawing.add(Line(75,y+77.5,950,y+77.5,strokeColor=colors.HexColor('#999999'),strokeWidth=0.4))
    drawing.add(String(75,y+177,title,fontName='Helvetica-Bold',fontSize=11))
    for number,(label,color) in enumerate(zip(labels,palette)):
        drawing.add(String(600+number*170,y+160,label,fontSize=9,fillColor=color))
drawing.add(String(440,47,'Tempo (ms)',fontSize=11))
drawing.add(String(75,25,'Trecho ilustrativo escolhido por conter uma falha sem controle; nao representa sozinho o desempenho total.',fontSize=9))
renderSVG.drawToFile(drawing,str(ROOT/'comparacao_etapa3.svg'))
print(f'Grafico criado: janela {window}, de {start*1000:.0f} a {end*1000:.0f} ms, usando curvas reais.')
