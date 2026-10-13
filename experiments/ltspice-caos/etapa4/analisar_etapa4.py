"""Le as medidas LTspice sem recalibrar a porta ou o criterio de acerto."""
from pathlib import Path
import csv
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
CASES={case['caso']:case for case in json.loads((ROOT/'casos_etapa4.json').read_text())}
GROUPS={group['grupo']:group for group in json.loads((ROOT/'grupos_etapa4.json').read_text())}


def parse(path):
    raw=path.read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',text,re.M)
    measures={}
    for name,block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',text,re.S):
        measures[name]={int(index):float(value) for index,value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',block,re.M)}
    if not steps:
        raise RuntimeError('Log sem passos: '+path.name)
    if len(steps)!=(32 if 'validacao' in path.name else 5):
        raise RuntimeError('Quantidade de passos inesperada ou simulacao incompleta.')
    rows=[]
    for step,line in enumerate(steps,1):
        parsed={name:float(value) for name,value in re.findall(r'(\w+)=([-+\d.eE]+)',line)}
        config=CASES[int(parsed['caso'])] if 'caso' in parsed else {'caso':-1,**GROUPS[int(parsed['grupo'])],'x_inicial':0.37,'passo':5e-6,'y_inicial':-0.2,'erro_sensor':0.0002}
        for index,code in enumerate(SEQUENCE):
            row={'arquivo':path.name,'passo':step,'caso':config['caso'],'grupo':config['grupo'],'latencia_us':round(config['latencia']*1e6,6),'tau_us':round(config['tau']*1e6,6),'limite_uA':round(config['limite_corrente']*1e6,6),'x_inicial':config['x_inicial'],'passo_tempo_us':round(config['passo']*1e6,6),'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for name in ('minimo','maximo','media','positivo','saturado','tracking'):
                row[name]=measures[f'{name}_{index:02}'][step]
            row['pico_corrente_uA']=measures['pico_corrente'][step]*1e6
            row['margem']=row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente']=int(row['margem']>0)
            rows.append(row)
    return rows


rows=[row for name in sys.argv[1:] for row in parse(ROOT/name)]
if not rows:
    raise SystemExit('Informe os logs concluidos.')
with (ROOT/'resultados_etapa4.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
summary=[]
for filename,group in sorted(set((row['arquivo'],row['grupo']) for row in rows)):
    subset=[row for row in rows if row['arquivo']==filename and row['grupo']==group]
    steps=set(row['passo'] for row in subset)
    summary.append({'arquivo':filename,'grupo':group,'latencia_us':subset[0]['latencia_us'],'tau_us':subset[0]['tau_us'],'limite_uA':subset[0]['limite_uA'],'execucoes':len(steps),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in steps),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'menor_margem':min(row['margem'] for row in subset),'pico_corrente_uA':max(row['pico_corrente_uA'] for row in subset),'fracao_saturada':sum(row['saturado'] for row in subset)/len(subset),'falhas':[{'passo':row['passo'],'janela':row['janela'],'margem':row['margem']} for row in subset if not row['acerto_persistente']]})
(ROOT/'resumo_etapa4.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in result.items() if key!='falhas'} for result in summary],indent=2,ensure_ascii=False))
