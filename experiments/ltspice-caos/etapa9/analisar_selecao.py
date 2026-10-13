"""Conta sinais de janelas LTspice e junta uso e deteccao do supervisor causal."""
from pathlib import Path
import json,csv,re,sys
ROOT=Path(__file__).resolve().parent
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
partial='--partial' in sys.argv
cases=json.loads((ROOT/'casos_selecao.json').read_text())
if (ROOT/'casos_refinamento.json').exists():cases+=json.loads((ROOT/'casos_refinamento.json').read_text())
rows=[];summary=[];pending=[]
for c in cases:
    path=ROOT/(c['nome']+'.log')
    if not path.exists():pending.append(c['nome']);continue
    raw=path.read_bytes();txt=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',txt,re.M)
    measures={n:{int(i):float(v) for i,v in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',b,re.M)} for n,b in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',txt,re.S)}
    required=[f'{n}_{i:02}' for i in range(17) for n in ['minimo','maximo']]+['pico_orcamento']
    if len(steps)!=2 or any(len(measures.get(k,{}))!=2 for k in required):pending.append(c['nome']);continue
    local=[]
    for s,step in enumerate(steps,1):
        initial=int(float(re.search(r'inicial=([\d.eE+-]+)',step).group(1)))
        peak=measures['pico_orcamento'][s]*1e6
        if peak>100.005:raise ValueError(f'Orcamento excedido {c["nome"]}: {peak}')
        for i,code in enumerate(SEQ):
            mn=measures[f'minimo_{i:02}'][s];mx=measures[f'maximo_{i:02}'][s];margin=mn if code==3 else -mx
            row={**c,'x_inicial':.37 if initial else -.37,'passo_ltspice':s,'janela':i,'A':code//2,'B':code%2,'minimo':mn,'maximo':mx,'margem':margin,'acerto':int(margin>0),'pico_orcamento_uA':peak}
            row.pop('estados_iniciais',None);local.append(row)
    rows+=local
    stats=json.loads((ROOT/(c['nome']+'_supervisor.json')).read_text())
    summary.append({**c,**stats,'janelas':len(local),'corretas':sum(r['acerto'] for r in local),'trajetorias_corretas':sum(all(r['acerto'] for r in local if r['passo_ltspice']==s) for s in [1,2]),'menor_margem':min(r['margem'] for r in local),'pico_orcamento_uA':max(r['pico_orcamento_uA'] for r in local)})
if pending and not partial:raise ValueError(f'{len(pending)} decks incompletos: {pending}')
if rows:
    keys=sorted(set(k for r in rows for k in r))
    with (ROOT/'resultados_selecao.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
(ROOT/'resumo_selecao.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'decks_concluidos':len(summary),'decks_pendentes':len(pending),'resultados':[{'perfil':r['perfil'],'politica':r['politica'],'seed':r['semente'],'passo_us':r['passo_us'],'acertos':f'{r["corretas"]}/{r["janelas"]}','media_ligados':round(r['media_ligados'],3)} for r in summary]},indent=2,ensure_ascii=False))
