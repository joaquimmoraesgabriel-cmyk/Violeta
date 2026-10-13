"""Compara zero, um e dois canais sob perturbacoes de parametros distintos."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]


def source(name,node,shift):
    pairs=[(0,(SEQUENCE[0]>>shift)&1)]
    for index in range(1,len(SEQUENCE)):
        pairs.extend([(index*0.05,(SEQUENCE[index-1]>>shift)&1),(index*0.05+1e-6,(SEQUENCE[index]>>shift)&1)])
    pairs.append((0.85,(SEQUENCE[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{time:.6f} {value}' for time,value in pairs)+')'


def deck(title,params,steps,all_traces=False):
    lines=[title,'.include MLC_dois_pilares.inc',source('Va','entrada_a',1),source('Vb','entrada_b',0)]+params+steps
    lines+=['.save V(x) V(saida) V(orcamento) V(saturado_a) V(saturado_b)']
    if all_traces:
        lines+=['.save V(y) V(entrada_a) V(entrada_b) V(pert_a) V(pert_b) V(ajuste_a) V(ajuste_b) I(Bcorrecao_a) I(Bcorrecao_b)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for index,code in enumerate(SEQUENCE):
        start,end=index*0.05+0.03,(index+1)*0.05-0.001
        for name,operation,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)'),('media','AVG','V(x)'),('positivo','AVG','V(saida)'),('saturado_a','AVG','V(saturado_a)'),('saturado_b','AVG','V(saturado_b)')]:
            lines.append(f'.meas tran {name}_{index:02} {operation} {trace} FROM {start:.6f} TO {end:.6f}')
    lines+=['.meas tran pico_orcamento MAX V(orcamento) FROM 0 TO 0.85','.end','']
    return '\n'.join(lines)


cases=[]
for case in range(48):
    cases.append({'caso':case,'perfil':case//16,'topologia':(case//4)%4,'x_inicial':0.37 if case%2 else -0.37,'y_inicial':-0.2,'passo_tempo_us':2.5 if (case//2)%2 else 5})
(ROOT/'casos_etapa6.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
(ROOT/'MLC_dois_pilares_validacao.cir').write_text(deck('* Ensaio: 3 perfis x 4 topologias x 2 estados x 2 passos.', ['.param caso=0 perfil=floor(caso/16) topologia=mod(floor(caso/4),4)','.param x_inicial=if(mod(caso,2),0.37,-0.37) y_inicial=-0.2 passo=if(mod(floor(caso/2),2),2.5u,5u)'],['.step param caso 0 47 1']),encoding='utf-8')
(ROOT/'MLC_dois_pilares_demo.cir').write_text(deck('* Demonstracao: duas perturbacoes, quatro topologias, orcamento total 100 uA.', ['.param perfil=2 x_inicial=0.37 y_inicial=-0.2 passo=5u'],['.step param topologia list 0 1 2 3'],True),encoding='utf-8')
print('Etapa 6 preparada: 48 trajetorias, 17 janelas cada; demonstracao com quatro topologias.')
