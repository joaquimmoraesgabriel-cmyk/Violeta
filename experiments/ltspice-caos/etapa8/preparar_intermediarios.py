"""Extensao declarada apos a demonstracao: 5 e 7 podem dispensar 9?"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
cases=[]
for n in [5,7]:
    for faults in [2,4]:
        for step in [5e-6,2.5e-6]:
            for x in [-.37,.37]:
                cases.append(dict(caso=len(cases),perfil=1,politica=2,atraso_coord=0,orcamento_max=100e-6,x_inicial=x,y_inicial=-.2,passo=step,nsub=n,falhas=faults,desvio_falha=.02))
original=(ROOT/'MLC_subpilares_validacao.cir').read_text().splitlines()
lines=['* Intermediarios: cinco e sete subpilares, duas ou quatro falhas.']
for line in original[1:]:
    if line.startswith('.param ') and 'table(caso,' in line:
        key=line.split()[1].split('=')[0]
        line=f'.param {key}=table(caso,'+','.join(f'{i},{c[key]}' for i,c in enumerate(cases))+')'
    if line.startswith('.step '): line=f'.step param caso 0 {len(cases)-1} 1'
    lines.append(line)
name='MLC_subpilares_intermediarios'
(ROOT/(name+'.cir')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')
print('16 trajetorias com 5 e 7 sensores preparadas.')
