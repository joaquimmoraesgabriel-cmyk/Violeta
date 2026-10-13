"""Avalia janelas inteiras e o orcamento agregado de correcao."""
from pathlib import Path
import csv
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
CASES={case['caso']:case for case in json.loads((ROOT/'casos_etapa6.json').read_text())}


def parse(path):
    raw=path.read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',text,re.M)
    if len(steps)!=(48 if 'validacao' in path.name else 4):
        raise RuntimeError('Log incompleto ou quantidade de passos inesperada.')
    measures={}
    for name,block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',text,re.S):
        measures[name]={int(index):float(value) for index,value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',block,re.M)}
    required=[f'{name}_{index:02}' for index in range(17) for name in ('minimo','maximo','media','positivo','saturado_a','saturado_b')]+['pico_orcamento']
    if any(len(measures.get(name,{}))!=len(steps) for name in required):
        raise RuntimeError('Medidas ainda ausentes ou incompletas: '+path.name)
    rows=[]
    for step,line in enumerate(steps,1):
        params={name:float(value) for name,value in re.findall(r'(\w+)=([-+\d.eE]+)',line)}
        config=CASES[int(params['caso'])] if 'caso' in params else {'caso':-1,'perfil':2,'topologia':int(params['topologia']),'x_inicial':0.37,'y_inicial':-0.2,'passo_tempo_us':5}
        for index,code in enumerate(SEQUENCE):
            row={'arquivo':path.name,'passo':step,**config,'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for name in ('minimo','maximo','media','positivo','saturado_a','saturado_b'):
                row[name]=measures[f'{name}_{index:02}'][step]
            row['pico_orcamento_uA']=measures['pico_orcamento'][step]*1e6
            if row['pico_orcamento_uA']>100.001:
                raise RuntimeError('Orcamento de correcao excedido.')
            row['margem']=row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente']=int(row['margem']>0)
            rows.append(row)
    return rows


rows=[row for filename in sys.argv[1:] for row in parse(ROOT/filename)]
if not rows:
    raise SystemExit('Informe os logs concluidos.')
with (ROOT/'resultados_etapa6.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
summary=[]
for filename,profile,topology in sorted(set((row['arquivo'],row['perfil'],row['topologia']) for row in rows)):
    subset=[row for row in rows if (row['arquivo'],row['perfil'],row['topologia'])==(filename,profile,topology)]
    steps=set(row['passo'] for row in subset)
    summary.append({'arquivo':filename,'perfil':profile,'topologia':topology,'execucoes':len(steps),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in steps),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'menor_margem':min(row['margem'] for row in subset),'pico_orcamento_uA':max(row['pico_orcamento_uA'] for row in subset),'saturacao_a':sum(row['saturado_a'] for row in subset)/len(subset),'saturacao_b':sum(row['saturado_b'] for row in subset)/len(subset),'falhas':[{'passo':row['passo'],'janela':row['janela'],'margem':row['margem']} for row in subset if not row['acerto_persistente']]})
(ROOT/'resumo_etapa6.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in result.items() if key!='falhas'} for result in summary],indent=2,ensure_ascii=False))
