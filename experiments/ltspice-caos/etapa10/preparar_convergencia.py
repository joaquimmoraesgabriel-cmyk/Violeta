"""Refinamento motivado pela mudanca de classificacao no desvio forte."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
template=(ROOT/'MLC_pilares_validacao.cir').read_text().splitlines()
cases=[]
for step in [1.25e-6,.625e-6]:
    for top in [3,7]:
        for x in [-.37,.37]:cases.append(dict(caso=len(cases),perfil_c=1,topologia=top,x_inicial=x,y_inicial=-.2,passo=step))
lines=[]
for line in template:
    if line.startswith('.param ') and 'table(caso,' in line:
        k=line.split()[1].split('=')[0];line=f'.param {k}=table(caso,'+','.join(f'{i},{c[k]}' for i,c in enumerate(cases))+')'
    if line.startswith('.step '):line=f'.step param caso 0 {len(cases)-1} 1'
    lines.append(line)
name='MLC_pilares_convergencia'
(ROOT/(name+'.cir')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')
print('Oito trajetorias: comparacao forte em 1,25 e 0,625 us.')
