from pathlib import Path
import json,csv,re,sys
ROOT=Path(__file__).resolve().parent
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
rows=[]
for name in sys.argv[1:]:
    cases=json.loads((ROOT/(name+'.json')).read_text())
    raw=(ROOT/(name+'.log')).read_bytes();txt=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',txt,re.M)
    measures={n:{int(i):float(v) for i,v in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',b,re.M)} for n,b in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',txt,re.S)}
    keys=[f'{n}_{i:02}' for i in range(17) for n in ['minimo','maximo']]+['pico_orcamento']
    if len(steps)!=len(cases) or any(len(measures.get(k,{}))!=len(cases) for k in keys):raise ValueError('Incompleto: '+name)
    for s,line in enumerate(steps,1):
        c=cases[int(float(re.search(r'caso=([\d.eE+-]+)',line).group(1)))];peak=measures['pico_orcamento'][s]*1e6
        if peak>100.005:raise ValueError(f'Orcamento: {peak}')
        for i,code in enumerate(SEQ):
            mn=measures[f'minimo_{i:02}'][s];mx=measures[f'maximo_{i:02}'][s];margin=mn if code==3 else -mx
            rows.append({'arquivo':name,**c,'janela':i,'A':code//2,'B':code%2,'minimo':mn,'maximo':mx,'margem':margin,'acerto':int(margin>0),'pico_orcamento_uA':peak})
with (ROOT/'resultados_pilares.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=[]
for key in sorted(set((r['arquivo'],r['perfil_c'],r['topologia'],r['passo']) for r in rows)):
    part=[r for r in rows if (r['arquivo'],r['perfil_c'],r['topologia'],r['passo'])==key]
    cs=set(r['caso'] for r in part)
    summary.append(dict(zip(['arquivo','perfil_c','topologia','passo'],key),janelas=len(part),corretas=sum(r['acerto'] for r in part),trajetorias_corretas=sum(all(r['acerto'] for r in part if r['caso']==c) for c in cs),menor_margem=min(r['margem'] for r in part),pico_orcamento_uA=max(r['pico_orcamento_uA'] for r in part)))
(ROOT/'resumo_pilares.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
