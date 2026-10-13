"""Le o mapa LTspice mantendo o criterio de sinal persistente."""
from pathlib import Path
import csv
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
CASES={case['caso']:case for case in json.loads((ROOT/'casos_etapa5.json').read_text())}


def parse(path):
    raw=path.read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',text,re.M)
    if len(steps)!=(72 if 'validacao' in path.name else 6):
        raise RuntimeError('Quantidade de passos inesperada ou simulacao incompleta.')
    measures={}
    for name,block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',text,re.S):
        measures[name]={int(index):float(value) for index,value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',block,re.M)}
    rows=[]
    for step,line in enumerate(steps,1):
        case=int(re.search(r'caso=([\d]+)',line).group(1))
        params=CASES[case]
        for index,code in enumerate(SEQUENCE):
            row={'arquivo':path.name,'passo':step,**params,'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for name in ('minimo','maximo','media','positivo','saturado','tracking'):
                row[name]=measures[f'{name}_{index:02}'][step]
            row['pico_corrente_uA']=measures['pico_corrente'][step]*1e6
            row['margem']=row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente']=int(row['margem']>0)
            rows.append(row)
    return rows


rows=[row for filename in sys.argv[1:] for row in parse(ROOT/filename)]
if not rows:
    raise SystemExit('Informe os logs concluidos.')
with (ROOT/'resultados_etapa5.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
summary=[]
keys=set((row['arquivo'],row['frequencia'],row['latencia_us']) for row in rows)
for filename,frequency,delay in sorted(keys,key=lambda item:(item[0],item[1],9999 if item[2] is None else item[2])):
    subset=[row for row in rows if (row['arquivo'],row['frequencia'],row['latencia_us'])==(filename,frequency,delay)]
    steps=set(row['passo'] for row in subset)
    summary.append({'arquivo':filename,'frequencia_Hz':frequency,'latencia_us':delay,'controle':int(delay is not None),'execucoes':len(steps),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in steps),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'menor_margem':min(row['margem'] for row in subset),'pico_corrente_uA':max(row['pico_corrente_uA'] for row in subset),'fracao_saturada':sum(row['saturado'] for row in subset)/len(subset),'falhas':[{'passo':row['passo'],'janela':row['janela'],'margem':row['margem']} for row in subset if not row['acerto_persistente']]})
(ROOT/'resumo_etapa5.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in item.items() if key!='falhas'} for item in summary],indent=2,ensure_ascii=False))
