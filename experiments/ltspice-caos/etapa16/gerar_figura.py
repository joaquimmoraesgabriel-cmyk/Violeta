"""Figura cientifica estaticamente reproduzivel com os graficos do ReportLab."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from reportlab.graphics.shapes import Drawing,Rect,String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor

ROOT=Path(__file__).resolve().parent
comp=json.loads((ROOT/'comparacoes.json').read_text(encoding='utf-8'))
data=list(comp['familias'].values())
fig=Drawing(960,700)
fig.add(Rect(0,0,960,700,fillColor=HexColor('#ffffff'),strokeColor=None))
fig.add(String(35,665,'Etapa 16 | Pilar E sob o mesmo orçamento de corrente',fontName='Helvetica-Bold',fontSize=21,fillColor=HexColor('#172238')))
fig.add(String(35,640,'Alta demanda • quatro condições do topo • 1,25 e 0,625 µs • dois estados iniciais',fontSize=11,fillColor=HexColor('#526073')))

def panel(x,y,title,series,maximum,step,colors):
    fig.add(String(x,y+235,title,fontName='Helvetica-Bold',fontSize=14,fillColor=HexColor('#172238')))
    chart=VerticalBarChart()
    chart.x=x+38;chart.y=y+25;chart.width=350;chart.height=190
    chart.data=series
    chart.categoryAxis.categoryNames=['Referência','E (20 µA)','Prioridade D']
    chart.categoryAxis.labels.fontName='Helvetica';chart.categoryAxis.labels.fontSize=10
    chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=maximum;chart.valueAxis.valueStep=step
    chart.valueAxis.labels.fontSize=9
    chart.valueAxis.strokeColor=HexColor('#a3afbd')
    chart.categoryAxis.strokeColor=HexColor('#a3afbd')
    chart.barSpacing=3;chart.groupSpacing=18
    for index,color in enumerate(colors):
        chart.bars[index].fillColor=HexColor(color);chart.bars[index].strokeColor=None
    fig.add(chart)

panel(35,360,'Janelas corretas (de 272)',[[d['acertos'] for d in data]],272,68,['#315a96'])
panel(500,360,'Resíduo da compensação (µA RMS)',[[d['rms_d'] for d in data],[d['rms_y'] for d in data]],60,15,['#315a96','#bb7829'])
fig.add(String(542,348,'Azul: D + E    |    Ocre: canal A–B–C',fontSize=10,fillColor=HexColor('#526073')))
panel(35,80,'Variação de g(x) (V/s do modelo)',[[d['variacao_g'] for d in data]],1200,300,['#315a96'])
panel(500,80,'Janelas corretas nos dois passos (de 136)',[[d['comuns'] for d in data]],136,34,['#315a96'])
fig.add(String(35,42,'Capacidade operacional: 90 µA. Os módulos das três correntes são somados no candidato E.',fontSize=11,fillColor=HexColor('#526073')))
fig.add(String(35,23,'g(x) é uma grandeza do modelo; o gráfico não representa estresse térmico. Valores exatos e limites no relatório.',fontSize=10,fillColor=HexColor('#526073')))
path=ROOT/'comparacao_pilar_E.svg'
renderSVG.drawToFile(fig,str(path))
root=ET.parse(path).getroot()
assert root.tag.endswith('svg')
assert len(root.findall('.//{http://www.w3.org/2000/svg}text'))>20
print(f'Figura SVG gerada e XML verificado: {path}')
