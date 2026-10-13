"""Figura vetorial usando ReportLab, com escalas fixas e denominadores explicitos."""
from pathlib import Path
import json
from reportlab.graphics.shapes import Drawing,String,Rect,Line
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'comparacoes.json').read_text(encoding='utf-8'))['familias']
names=['referencia','comum_E','grupos_E'];labels=['Referencia','Comum + E','Grupos + E']
colors=[HexColor('#52677D'),HexColor('#167C80'),HexColor('#C88220')]
d=Drawing(970,640)
d.add(Rect(0,0,970,640,fillColor=HexColor('#F7F9FB'),strokeColor=None))
def text(x,y,s,size=12,color='#152538',font='Helvetica'):
    d.add(String(x,y,s,fontName=font,fontSize=size,fillColor=HexColor(color)))
text(32,605,'Etapa 17 | Quem distribui os 90 uA?',23,font='Helvetica-Bold')
text(32,581,'Alta demanda: mesmas 16 trajetorias por arquitetura, quatro condicoes do topo.',12)
def bars(x,y,title,key,maximum,unit,decimals=0):
    text(x,y+172,title,14,font='Helvetica-Bold')
    w=270
    for i,(name,label,col) in enumerate(zip(names,labels,colors)):
        yy=y+122-i*48;v=data[name][key]
        text(x,yy+4,label,11)
        d.add(Rect(x+95,yy-2,w,19,fillColor=HexColor('#E5EAF0'),strokeColor=None))
        d.add(Rect(x+95,yy-2,w*v/maximum,19,fillColor=col,strokeColor=None))
        text(x+373,yy+3,f'{v:.{decimals}f}',11)
    text(x+95,y-8,f'0 a {maximum:g} {unit}',10,'#516174')
bars(32,358,'Janelas corretas (de 272)','corretas',272,'janelas')
bars(508,358,'Corretas nos dois passos (de 136)','comuns',136,'pares')
bars(32,120,'Residual de compensacao em Y','rms_residuo_y_uA',60,'uA; menor e melhor',2)
bars(508,120,'Residual de compensacao em D + E','rms_residuo_d_uA',30,'uA; menor e melhor',2)
text(32,64,'Grupos: ABC / D+E. E atua ate 5 uA dentro do total; novas cotas com atraso de 20 us e RC de 50 us.',11)
text(32,44,'Corrente aprovada nao significa logica validada. Consulte o relatorio para falhas e terceiro passo.',11)
renderSVG.drawToFile(d,str(ROOT/'comparacao_coordenadores.svg'))
import xml.etree.ElementTree as ET
ET.parse(ROOT/'comparacao_coordenadores.svg')
print('Figura SVG criada e estrutura XML verificada.')
