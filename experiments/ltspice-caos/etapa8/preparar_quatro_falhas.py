"""Refinamento adicional da condicao que distingue nove sensores."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
cases=[dict(c,caso=i,passo=2.5e-6) for i,c in enumerate(c for c in json.loads((ROOT/'MLC_subpilares_validacao.json').read_text()) if c['nsub']==9 and c['falhas']==4)]
lines=[]
for line in (ROOT/'MLC_subpilares_validacao.cir').read_text().splitlines():
    if line.startswith('.param ') and 'table(caso,' in line:
        key=line.split()[1].split('=')[0]
        line=f'.param {key}=table(caso,'+','.join(f'{i},{c[key]}' for i,c in enumerate(cases))+')'
    if line.startswith('.step '): line=f'.step param caso 0 {len(cases)-1} 1'
    lines.append(line)
name='MLC_subpilares_quatro_falhas'
(ROOT/(name+'.cir')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')
print('Duas trajetorias de nove sensores e quatro falhas com passo menor.')
