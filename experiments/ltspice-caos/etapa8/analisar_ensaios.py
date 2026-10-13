"""Analisa extremos das janelas reais; nao infere acertos de medias."""
from pathlib import Path
import csv,json,re,sys
ROOT=Path(__file__).resolve().parent
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
def parse(name):
    cases=json.loads((ROOT/(name+'.json')).read_text())
    raw=(ROOT/(name+'.log')).read_bytes()
    txt=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',txt,re.M)
    if len(steps)!=len(cases): raise ValueError(f'{name}: passos incompletos {len(steps)}/{len(cases)}')
    measures={n:{int(i):float(v) for i,v in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',b,re.M)} for n,b in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',txt,re.S)}
    required=[f'{n}_{i:02}' for i in range(17) for n in ['minimo','maximo','positivo']]+['pico_orcamento']
    for key in required:
        if len(measures.get(key,{}))!=len(cases): raise ValueError(f'{name}: medida incompleta {key}')
    rows=[]
    for s,line in enumerate(steps,1):
        case=int(re.search(r'caso=([\d.eE+-]+)',line).group(1))
        cfg=cases[case]
        peak=measures['pico_orcamento'][s]*1e6
        if peak>cfg['orcamento_max']*1e6+.005: raise ValueError(f'Orcamento ultrapassado: {name} caso{case}, {peak}')
        for i,code in enumerate(SEQ):
            mn,mx=measures[f'minimo_{i:02}'][s],measures[f'maximo_{i:02}'][s]
            margin=mn if code==3 else -mx
            rows.append({'arquivo':name,'passo_ltspice':s,**cfg,'janela':i,'A':code//2,'B':code%2,'esperado':int(code==3),'minimo':mn,'maximo':mx,'margem':margin,'acerto':int(margin>0),'fracao_positivo':measures[f'positivo_{i:02}'][s],'pico_orcamento_uA':peak})
    return rows
rows=[row for name in sys.argv[1:] for row in parse(name)]
keys=sorted(set(k for r in rows for k in r))
with (ROOT/'resultados_ensaios.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
summary=[]
def groupkey(r):
    return tuple(r.get(k) for k in ['arquivo','politica','atraso_coord','orcamento_max','nsub','falhas','passo'])
for group in sorted(set(groupkey(r) for r in rows),key=str):
    part=[r for r in rows if groupkey(r)==group]
    steps=set(r['passo_ltspice'] for r in part)
    item=dict(zip(['arquivo','politica','atraso_coord','orcamento_max','nsub','falhas','passo'],group))
    item.update(janelas=len(part),corretas=sum(r['acerto'] for r in part),trajetorias=len(steps),trajetorias_corretas=sum(all(r['acerto'] for r in part if r['passo_ltspice']==s) for s in steps),menor_margem=min(r['margem'] for r in part),pico_orcamento_uA=max(r['pico_orcamento_uA'] for r in part))
    summary.append(item)
(ROOT/'resumo_ensaios.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
