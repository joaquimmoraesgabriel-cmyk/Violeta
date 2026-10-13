"""Medidas LTspice completas para D e coordenadores; extremos e capacidade."""
from pathlib import Path
import json,csv,re,sys
ROOT=Path(sys.argv[1]).resolve()
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
rows=[]
for name in sys.argv[2:]:
    cases=json.loads((ROOT/(name+'.json')).read_text())
    raw=(ROOT/(name+'.log')).read_bytes();txt=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',txt,re.M)
    m={n:{int(i):float(v) for i,v in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',b,re.M)} for n,b in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',txt,re.S)}
    req=[f'{n}_{i:02}' for i in range(17) for n in ['minimo','maximo']]+['pico_orcamento']
    if 'politica_coord' in cases[0]:req+=['pico_sem_protecao','uso_protecao','uso_reserva','sobra','falta']
    if len(steps)!=len(cases) or any(len(m.get(k,{}))!=len(cases) for k in req):raise ValueError('Incompleto: '+name)
    for s,line in enumerate(steps,1):
        c=cases[int(float(re.search(r'caso=([\d.eE+-]+)',line).group(1)))];peak=m['pico_orcamento'][s]*1e6
        if peak>100.005 and 'politica_coord' not in c:raise ValueError(f'Orcamento excedido {name} caso={c["caso"]}: {peak}')
        for i,code in enumerate(SEQ):
            mn=m[f'minimo_{i:02}'][s];mx=m[f'maximo_{i:02}'][s];margin=mn if code==3 else -mx
            r={'arquivo':name,**c,'janela':i,'A':code//2,'B':code%2,'minimo':mn,'maximo':mx,'margem':margin,'acerto':int(margin>0),'pico_orcamento_uA':peak,'pico_orcamento_fora_tolerancia':int(peak>100.005)}
            for k in req:
                if '_' not in k or k in ['pico_sem_protecao','uso_protecao','uso_reserva']:
                    if k not in ['pico_orcamento']:r[k]=m[k][s]
            rows.append(r)
keys=sorted(set(k for r in rows for k in r))
with (ROOT/'resultados.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
groups=['arquivo','perfil','topologia','politica_coord','falha_coord','passo']
summary=[]
for key in sorted(set(tuple(r.get(k) for k in groups) for r in rows),key=str):
    p=[r for r in rows if tuple(r.get(k) for k in groups)==key];cs=set(r['caso'] for r in p)
    r=dict(zip(groups,key),janelas=len(p),corretas=sum(r['acerto'] for r in p),trajetorias_corretas=sum(all(v['acerto'] for v in p if v['caso']==c) for c in cs),menor_margem=min(v['margem'] for v in p),pico_orcamento_uA=max(v['pico_orcamento_uA'] for v in p),trajetorias_fora_tolerancia=sum(any(v['pico_orcamento_fora_tolerancia'] for v in p if v['caso']==c) for c in cs))
    if 'politica_coord' in p[0]:
        for metric in ['pico_sem_protecao','uso_protecao','uso_reserva','sobra','falta']:
            r[metric+'_max']=max(v[metric] for v in p)
    summary.append(r)
(ROOT/'resumo.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
