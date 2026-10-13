"""Gera testes com criterio e casos fixados antes das simulacoes."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]


def source(name,node,shift,sequence=SEQUENCE):
    pairs=[(0,(sequence[0]>>shift)&1)]
    for index in range(1,len(sequence)):
        pairs.extend([(index*0.05,(sequence[index-1]>>shift)&1),(index*0.05+1e-6,(sequence[index]>>shift)&1)])
    pairs.append((len(sequence)*0.05,(sequence[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+ ' '.join(f'{time:.6f} {value}' for time,value in pairs)+')'


def deck(title,params,steps,save_all=False,sequence=SEQUENCE):
    lines=[title,'.include MLC_dinamico.inc',source('Va','entrada_a',1,sequence),source('Vb','entrada_b',0,sequence)]+params+steps
    lines+=['.save V(x) V(saida) V(saturacao) V(tracking) I(Bcorrecao)']
    if save_all:
        lines+=['.save V(y) V(entrada_a) V(entrada_b) V(perturbacao) V(ajuste) V(estimativa) V(filtrado)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for index,code in enumerate(sequence):
        start,end=index*0.05+0.03,(index+1)*0.05-0.001
        for measure,operation,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)'),('media','AVG','V(x)'),('positivo','AVG','V(saida)'),('saturado','AVG','V(saturacao)'),('tracking','RMS','V(tracking)')]:
            lines.append(f'.meas tran {measure}_{index:02} {operation} {trace} FROM {start:.6f} TO {end:.6f}')
    lines+=['.meas tran pico_corrente MAX abs(I(Bcorrecao)) FROM 0 TO 0.85','.end','']
    return '\n'.join(lines)


demo_params=['.param perfil=1 x_inicial=0 y_inicial=-0.2 erro_sensor=0.0002 passo=5u']
(ROOT/'MLC_dinamico_demo.cir').write_text(deck('* Demonstracao: mudancas durante a leitura e limites do pilar.',demo_params,['.step param modo list 0 1 2 3'],True),encoding='utf-8')
limit_params=['.param perfil=2 x_inicial=0.37 y_inicial=-0.2 erro_sensor=0.0002 passo=5u']
(ROOT/'MLC_dinamico_limite.cir').write_text(deck('* Demonstracao de limite: perturbacao rapida e quatro modos de controle.',limit_params,['.step param modo list 0 1 2 3'],True),encoding='utf-8')
cases=[]
for case in range(48):
    cases.append({'caso':case,'perfil':case//16,'modo':(case%16)//4,'x_inicial':0.37 if case%2 else -0.37,'y_inicial':-0.2,'erro_sensor':0.0002,'passo':2.5e-6 if (case//2)%2 else 5e-6})
params=['.param caso=0','.param perfil=floor(caso/16) modo=floor(mod(caso,16)/4)','.param x_inicial=if(mod(caso,2),0.37,-0.37) y_inicial=-0.2','.param erro_sensor=0.0002 passo=if(mod(floor(caso/2),2),2.5u,5u)']
(ROOT/'MLC_dinamico_validacao.cir').write_text(deck('* Ensaio: 3 perturbacoes x 4 modos x 2 estados x 2 passos.',params,['.step param caso 0 47 1']),encoding='utf-8')
(ROOT/'casos_etapa3.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
print('Etapa 3 preparada: demonstracao com 4 modos; avaliacao com 48 trajetorias, 17 janelas cada.')
