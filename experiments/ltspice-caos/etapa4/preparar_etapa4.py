"""Ensaio fatorial 2x2x2: separa efeitos e revela interacoes."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
previous=(ROOT.parent/'etapa3'/'MLC_dinamico.inc').read_text(encoding='utf-8')
model='\n'.join(line for line in previous.splitlines() if not line.startswith(('.param latencia=','.param tau=','.param limite_corrente=')))+'\n'
(ROOT/'MLC_fatores.inc').write_text(model,encoding='utf-8')


def source(name,node,shift):
    pairs=[(0,(SEQUENCE[0]>>shift)&1)]
    for index in range(1,len(SEQUENCE)):
        pairs.extend([(index*0.05,(SEQUENCE[index-1]>>shift)&1),(index*0.05+1e-6,(SEQUENCE[index]>>shift)&1)])
    pairs.append((0.85,(SEQUENCE[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{time:.6f} {value}' for time,value in pairs)+')'


def deck(title,params,steps,save_all=False):
    lines=[title,'.include MLC_fatores.inc',source('Va','entrada_a',1),source('Vb','entrada_b',0),'.param modo=2 perfil=2 erro_sensor=0.0002 y_inicial=-0.2']
    lines+=params+['.param latencia=if(mod(grupo,2),500u,50u)','.param tau=if(mod(floor(grupo/2),2),1m,100u)','.param limite_corrente=if(floor(grupo/4),20u,100u)']+steps
    lines+=['.save V(x) V(saida) V(saturacao) V(tracking) I(Bcorrecao)']
    if save_all:
        lines+=['.save V(y) V(entrada_a) V(entrada_b) V(perturbacao) V(ajuste)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for index,code in enumerate(SEQUENCE):
        start,end=index*0.05+0.03,(index+1)*0.05-0.001
        for name,operation,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)'),('media','AVG','V(x)'),('positivo','AVG','V(saida)'),('saturado','AVG','V(saturacao)'),('tracking','RMS','V(tracking)')]:
            lines.append(f'.meas tran {name}_{index:02} {operation} {trace} FROM {start:.6f} TO {end:.6f}')
    lines+=['.meas tran pico_corrente MAX abs(I(Bcorrecao)) FROM 0 TO 0.85','.end','']
    return '\n'.join(lines)


groups=[]
cases=[]
for group in range(8):
    config={'grupo':group,'latencia':(500 if group%2 else 50)*1e-6,'tau':(1000 if (group//2)%2 else 100)*1e-6,'limite_corrente':(20 if group//4 else 100)*1e-6}
    groups.append(config)
    for variant in range(4):
        cases.append({'caso':group*4+variant,**config,'x_inicial':0.37 if variant%2 else -0.37,'passo':2.5e-6 if variant//2 else 5e-6,'y_inicial':-0.2,'erro_sensor':0.0002})
(ROOT/'MLC_fatores_validacao.cir').write_text(deck('* Fatorial: 8 configuracoes x 2 estados x 2 passos.', ['.param caso=0 grupo=floor(caso/4)','.param x_inicial=if(mod(caso,2),0.37,-0.37) passo=if(mod(floor(caso/2),2),2.5u,5u)'],['.step param caso 0 31 1']),encoding='utf-8')
(ROOT/'MLC_fatores_demo.cir').write_text(deck('* Demonstracao: base, uma alteracao de cada vez, e tres alteracoes juntas.', ['.param x_inicial=0.37 passo=5u'],['.step param grupo list 0 1 2 4 7'],True),encoding='utf-8')
(ROOT/'casos_etapa4.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
(ROOT/'grupos_etapa4.json').write_text(json.dumps(groups,indent=2),encoding='utf-8')
print('Etapa 4 preparada: 32 trajetorias fatoriais e demonstracao com cinco configuracoes.')
