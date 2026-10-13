"""Mapa predefinido de latencias e frequencias, com comparacao desligada."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
DELAYS=[50,100,200,350,500]
FREQUENCIES=[100,500,1000]
source_model=(ROOT.parent/'etapa4'/'MLC_fatores.inc').read_text(encoding='utf-8')
source_model=source_model.replace('Vrapido rapido 0 SINE(0 0.005 500)','Vrapido rapido 0 SINE(0 0.005 {frequencia})')
(ROOT/'MLC_mapa.inc').write_text(source_model,encoding='utf-8')


def source(name,node,shift):
    pairs=[(0,(SEQUENCE[0]>>shift)&1)]
    for index in range(1,len(SEQUENCE)):
        pairs.extend([(index*0.05,(SEQUENCE[index-1]>>shift)&1),(index*0.05+1e-6,(SEQUENCE[index]>>shift)&1)])
    pairs.append((0.85,(SEQUENCE[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{time:.6f} {value}' for time,value in pairs)+')'


def deck(title,steps,save_all=False):
    lines=[title,'.include MLC_mapa.inc',source('Va','entrada_a',1),source('Vb','entrada_b',0),
        '.param caso=25 configuracao=mod(floor(caso/4),6)',
        '.param frequencia=table(floor(caso/24),0,100,1,500,2,1000)',
        '.param latencia=table(configuracao,0,50u,1,100u,2,200u,3,350u,4,500u,5,50u)',
        '.param modo=if(configuracao>4.5,0,2) perfil=2',
        '.param tau=100u limite_corrente=20u erro_sensor=0.0002 y_inicial=-0.2',
        '.param x_inicial=if(mod(caso,2),0.37,-0.37) passo=if(mod(floor(caso/2),2),2.5u,5u)',
    ]+steps+['.save V(x) V(saida) V(saturacao) V(tracking) I(Bcorrecao)']
    if save_all:
        lines+=['.save V(y) V(entrada_a) V(entrada_b) V(perturbacao) V(ajuste)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for index,code in enumerate(SEQUENCE):
        start,end=index*0.05+0.03,(index+1)*0.05-0.001
        for name,operation,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)'),('media','AVG','V(x)'),('positivo','AVG','V(saida)'),('saturado','AVG','V(saturacao)'),('tracking','RMS','V(tracking)')]:
            lines.append(f'.meas tran {name}_{index:02} {operation} {trace} FROM {start:.6f} TO {end:.6f}')
    lines+=['.meas tran pico_corrente MAX abs(I(Bcorrecao)) FROM 0 TO 0.85','.end','']
    return '\n'.join(lines)


cases=[]
for case in range(72):
    config=(case//4)%6
    cases.append({'caso':case,'frequencia':FREQUENCIES[case//24],'controle':int(config<5),'latencia_us':DELAYS[config] if config<5 else None,'tau_us':100,'limite_uA':20,'x_inicial':0.37 if case%2 else -0.37,'y_inicial':-0.2,'erro_sensor':0.0002,'passo_tempo_us':2.5 if (case//2)%2 else 5})
(ROOT/'casos_etapa5.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
(ROOT/'MLC_mapa_validacao.cir').write_text(deck('* Mapa de latencias: 3 frequencias x 6 configuracoes x 4 variantes.',['.step param caso 0 71 1']),encoding='utf-8')
(ROOT/'MLC_mapa_demo.cir').write_text(deck('* Demonstracao: 500 Hz, cinco atrasos e pilar desligado.',['.step param caso list 25 29 33 37 41 45'],True),encoding='utf-8')
print('Etapa 5: 72 trajetorias predefinidas e demonstracao com seis configuracoes a 500 Hz.')
