"""Mapa comparativo das contagens reais dos dois canais."""
from pathlib import Path
import json
from reportlab.graphics.shapes import Drawing,String,Rect
from reportlab.graphics import renderSVG
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
summary=json.loads((ROOT/'resumo_etapa6.json').read_text(encoding='utf-8'))
results={(item['perfil'],item['topologia']):item for item in summary if item['arquivo']=='MLC_dois_pilares_validacao.log'}
if len(results)!=12:
    raise RuntimeError('Esperados os 12 grupos concluidos.')
drawing=Drawing(1000,425)
drawing.add(String(35,390,'Uma porta, dois canais de correcao',fontName='Helvetica-Bold',fontSize=20))
drawing.add(String(35,368,'Mesma capacidade total de correcao: 100 uA. Quatro trajetorias e 68 janelas por celula.',fontSize=11))
for column,label in enumerate(['Desligado','So canal A','So canal B','Dois canais']):
    drawing.add(String(270+column*170,325,label,fontName='Helvetica-Bold',fontSize=12,textAnchor='middle'))
for row,label in enumerate(['Perturbacao A','Perturbacao B','A e B juntas']):
    y=245-row*72
    drawing.add(String(35,y+26,label,fontSize=12))
    for column in range(4):
        item=results[(row,column)]
        score=item['janelas_corretas']/item['janelas']
        color=colors.HexColor('#29766b') if score==1 else colors.Color(0.85,0.40+0.30*score,0.30+0.30*score)
        drawing.add(Rect(190+column*170,y,160,60,fillColor=color,strokeColor=colors.white))
        drawing.add(String(270+column*170,y+20,f"{item['janelas_corretas']}/{item['janelas']}",fontName='Helvetica-Bold',fontSize=19,fillColor=colors.white,textAnchor='middle'))
drawing.add(String(35,66,'A: amortecimento. B: deslocamento de bias. Sensores e atuadores ainda sao modelos ideais com erros definidos.',fontSize=10))
drawing.add(String(35,44,'Verde: todas as janelas passaram neste conjunto; nao e garantia de funcionamento fora das condicoes simuladas.',fontSize=10))
renderSVG.drawToFile(drawing,str(ROOT/'comparacao_dois_pilares.svg'))
print('comparacao_dois_pilares.svg criado com as medidas reais.')
