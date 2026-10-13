"""Figuras cientificas vetoriais; PNG por render PDF em memoria para inspecao."""
from pathlib import Path
import io,json,sys
import numpy as np
from reportlab.graphics.shapes import Drawing,String,Rect,Line,PolyLine
from reportlab.graphics import renderSVG,renderPDF
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
S={s['arquivo']:s for s in json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))}
T=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
D=json.loads((ROOT/'comparacoes.json').read_text(encoding='utf-8'))['diagnosticos']

def text(d,x,y,s,size=12,col='#182C3C',bold=False):
    font='Helvetica-Bold' if bold else 'Helvetica'
    assert 0<=x and x+stringWidth(s,font,size)<=d.width+1,(s,x)
    d.add(String(x,y,s,fontName=font,fontSize=size,fillColor=HexColor(col)))

def save(d,name):
    renderSVG.drawToFile(d,str(ROOT/f'{name}.svg'))
    stream=io.BytesIO();renderPDF.drawToFile(d,stream)
    pdf=pdfium.PdfDocument(stream.getvalue());page=pdf[0]
    bitmap=page.render(scale=1.5);pil=bitmap.to_pil();pil.save(ROOT/f'{name}.png')
    bitmap.close();page.close();pdf.close()

d=Drawing(980,760);d.add(Rect(0,0,980,760,fillColor=HexColor('#F7F9FB'),strokeColor=None))
text(d,30,722,'Etapa 18 | Cotas de corrente e recuperacao',23,bold=True)
text(d,30,696,'LTspice: 64 trajetorias novas. E participa do mesmo orcamento de 90 uA.',12)

def bars(x,y,title,items,maximum,footer):
    text(d,x,y+154,title,14,bold=True)
    for i,(label,value,color,denom) in enumerate(items):
        yy=y+113-i*42
        text(d,x,yy+3,label,11)
        d.add(Rect(x+120,yy-2,235,18,fillColor=HexColor('#E2E8ED'),strokeColor=None))
        d.add(Rect(x+120,yy-2,235*value/maximum,18,fillColor=HexColor(color),strokeColor=None))
        text(d,x+365,yy+2,f'{value}/{denom}',11,bold=True)
    text(d,x,y-5,footer,10,col='#506478')

bars(30,455,'Cota Y=0 / D=90: janelas corretas',[
    ('Reserva off',S['C_vies_off']['corretas'],'#A55650',68),
    ('Reserva on',S['C_vies_on']['corretas'],'#197A85',68),
    ('Saudavel on',S['C_sadio_on']['corretas'],'#65798C',68)],68,'Duas condicoes iniciais; passos maximos 1.25 / 0.625 us.')
bars(515,455,'L2 saudavel: janelas corretas',[
    ('20/50 us, off',S['L2_20_50_off']['corretas'],'#65798C',68),
    ('5/10 us, off',S['L2_5_10_off']['corretas'],'#C3862C',68),
    ('5/10 us, V2',S['L2_5_10_v2']['corretas'],'#197A85',68)],68,'Atraso / RC. Off desabilita apenas a comutacao do fiscal.')
bars(30,225,'L2 5/10 saudavel: alarmes indevidos',[
    ('Fiscal V1',D['L2_5_10']['alarmes_indevidos'],'#A55650',4),
    ('Fiscal V2',D['L2_5_10_v2']['alarmes_indevidos'],'#197A85',4)],4,'Contagem de trajetorias, nao janelas; menor e melhor.')
bars(515,225,'L2 V2: falhas de cota detectadas',[
    ('Replay',D['L2_replay_v2']['deteccoes'],'#197A85',2),
    ('Vies extremo',D['L2_vies_v2']['deteccoes'],'#197A85',2)],2,'Exploratorio: duas condicoes, apenas passo 0.625 us.')
d.add(Rect(30,123,920,85,fillColor=HexColor('#FFF0E5'),strokeColor=None))
false_corners=sum(D[n]['alarmes_indevidos'] for n in ['C_tolerancia_mais','C_tolerancia_menos'])
text(d,45,184,f'Pendencia: V1 alarmou em {false_corners}/4 trajetorias saudaveis nos cantos de tolerancia.',13,bold=True,col='#8B4035')
text(d,45,162,'V2 ainda nao foi testada nesses cantos nem no terceiro passo.',12)
text(d,45,140,f"Picos: shunts {max(t['pico_resistores_uA'] for t in T):.3f} uA; sondas 0 V {max(t['pico_sondas_uA'] for t in T):.3f} uA. Divergencia numerica pendente.",12)
text(d,30,80,'V2 muda a confirmacao RC de 20/40 us para 50/20 us; limiar de discrepancia permanece 6.5 uA.',11)
text(d,30,57,'Uma nota maior nao prova convergencia numerica. Consulte o relatorio para terceiro passo e tolerancias.',11)
text(d,30,34,'Os modelos ainda combinam atuadores genericos com controle comportamental; nao validam uma PCB.',11)
save(d,'comparacao_etapa18')

# Diagnostico do primeiro percurso saudavel, com as duas confirmacoes.
d=Drawing(980,640);d.add(Rect(0,0,980,640,fillColor=HexColor('#F7F9FB'),strokeColor=None))
text(d,30,605,'Por que revisar a confirmacao?',23,bold=True)
text(d,30,580,'L2 5/10 us saudavel, primeira condicao inicial, passo maximo 1.25 us.',12)
colors=['#A55650','#197A85'];data=[]
for name in ['L2_5_10','L2_5_10_v2']:
    cases=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
    t,c=next(raw_steps(ROOT/f'{name}.raw',4,max_last_gaps=[p['passo'] for p in cases]));m=(t>=.0021)&(t<=.0024)
    data.append((t[m]*1e6,c['v(erro_cota)'][m].astype(float)*1e6,c['v(timer_cota)'][m].astype(float),c['v(reserva_cota)'][m].astype(float)))
for panel,(title,column,maximum,threshold) in enumerate([('Discrepancia das cotas (uA)',1,16,6.5),('Estado da confirmacao RC',2,1,.7)]):
    x0=75;y0=340 if panel==0 else 115;w=850;h=165
    text(d,x0,y0+h+20,title,14,bold=True)
    for val in np.linspace(0,maximum,5):
        yy=y0+h*val/maximum;d.add(Line(x0,yy,x0+w,yy,strokeColor=HexColor('#DDE5EC'),strokeWidth=.5))
        text(d,35,yy-3,f'{val:g}',10)
    yy=y0+h*threshold/maximum;d.add(Line(x0,yy,x0+w,yy,strokeColor=HexColor('#404E5C'),strokeWidth=1,strokeDashArray=[4,3]))
    for values,color in zip(data,colors):
        xx=x0+w*(values[0]-2100)/300;yy=y0+h*np.minimum(values[column],maximum)/maximum
        points=np.column_stack([xx,yy]).ravel().tolist()
        d.add(PolyLine(points,strokeColor=HexColor(color),strokeWidth=1.2,fillColor=None))
    for val in [2100,2200,2300,2400]:text(d,x0+w*(val-2100)/300-12,y0-17,str(val),10)
text(d,720,74,'Tempo desde a partida (us)',11)
text(d,75,54,'V1: carga/descarga 20/40 us',11,col=colors[0])
text(d,390,54,'V2: carga/descarga 50/20 us',11,col=colors[1])
text(d,75,30,'Linhas tracejadas: limiares. Trajetorias podem divergir apos a comutacao; sao sinais medidos no RAW.',10)
save(d,'diagnostico_confirmacao')
print('Duas figuras SVG e PNG criadas.')
