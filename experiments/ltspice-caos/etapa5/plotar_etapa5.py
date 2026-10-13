"""Mapa SVG a partir das contagens reais do LTspice."""
from pathlib import Path
import json
from reportlab.graphics.shapes import Drawing,String,Rect
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
summary=json.loads((ROOT/'resumo_etapa5.json').read_text(encoding='utf-8'))
records={(item['frequencia_Hz'],item['latencia_us']):item for item in summary if item['arquivo']=='MLC_mapa_validacao.log'}
if len(records)!=18:
    raise RuntimeError('Esperadas 18 configuracoes concluidas.')
freqs=[100,500,1000]; delays=[50,100,200,350,500,None]
drawing=Drawing(830,570)
drawing.add(String(35,535,'Mapa de funcionamento do pilar',fontName='Helvetica-Bold',fontSize=19))
drawing.add(String(35,513,'Resposta fixa: 100 us. Corrente limitada: +/-20 uA. Perturbacao: +/-0,5%.',fontSize=11))
drawing.add(String(35,493,'Cada celula: janelas corretas / 68, em quatro trajetorias.',fontSize=10))
for column,frequency in enumerate(freqs):
    drawing.add(String(270+column*175,458,f'{frequency} Hz',fontName='Helvetica-Bold',fontSize=12,textAnchor='middle'))
for row,delay in enumerate(delays):
    y=388-row*58
    label='Desligado' if delay is None else f'Atraso: {delay} us'
    drawing.add(String(35,y+23,label,fontSize=12))
    for column,frequency in enumerate(freqs):
        item=records[(frequency,delay)]
        score=item['janelas_corretas']/item['janelas']
        color=colors.HexColor('#29766b') if score==1 else colors.Color(0.88,0.42+0.30*score,0.30+0.30*score)
        drawing.add(Rect(185+column*175,y,165,48,fillColor=color,strokeColor=colors.white))
        drawing.add(String(267.5+column*175,y+17,f"{item['janelas_corretas']}/{item['janelas']}",fontName='Helvetica-Bold',fontSize=17,fillColor=colors.white,textAnchor='middle'))
drawing.add(String(35,30,'Verde: todas as janelas passaram neste conjunto. Nao indica garantia fora das condicoes testadas.',fontSize=10))
drawing.add(String(35,12,'Os atrasos e frequencias entre as celulas nao foram avaliados; nao interpolamos uma fronteira de seguranca.',fontSize=9))
renderSVG.drawToFile(drawing,str(ROOT/'mapa_funcionamento.svg'))
print('Mapa gerado com as 18 configuracoes reais do ensaio.')
