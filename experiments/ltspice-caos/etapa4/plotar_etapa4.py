"""Grafico comparativo com contagens reais do ensaio fatorial."""
from pathlib import Path
import json
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
summary=json.loads((ROOT/'resumo_etapa4.json').read_text(encoding='utf-8'))
groups=sorted((item for item in summary if item['arquivo']=='MLC_fatores_validacao.log'),key=lambda item:item['grupo'],reverse=True)
if len(groups)!=8:
    raise RuntimeError('Esperados os oito grupos concluidos.')
drawing=Drawing(1050,580)
drawing.add(String(35,545,'Separando os fatores do pilar',fontName='Helvetica-Bold',fontSize=19))
drawing.add(String(35,523,'Perturbacao de 500 Hz: quatro trajetorias por configuracao; 17 janelas por trajetoria.',fontSize=11))
chart=HorizontalBarChart()
chart.x=360; chart.y=75; chart.width=600; chart.height=410
chart.data=[tuple(item['janelas_corretas'] for item in groups)]
chart.categoryAxis.categoryNames=[f"G{item['grupo']}: atraso {item['latencia_us']:.0f} us | resposta {item['tau_us']:.0f} us | {item['limite_uA']:.0f} uA" for item in groups]
chart.categoryAxis.labels.fontSize=10
chart.valueAxis.valueMin=0; chart.valueAxis.valueMax=68; chart.valueAxis.valueSteps=[0,17,34,51,68]
chart.valueAxis.labels.fontSize=10
chart.bars[0].fillColor=colors.HexColor('#286d62')
chart.bars[0].strokeColor=None
chart.barLabelFormat='%d'; chart.barLabels.fontSize=10
drawing.add(chart)
drawing.add(String(480,40,'Janelas corretas (maximo 68 por configuracao)',fontSize=11))
drawing.add(String(35,18,'Contagens de ensaios deterministas; nao representam uma probabilidade de sucesso em hardware.',fontSize=10))
renderSVG.drawToFile(drawing,str(ROOT/'comparacao_fatores.svg'))
print('comparacao_fatores.svg gerado a partir das contagens reais.')
