"""Contagens das medidas reais e verificacao do orcamento comum."""
from pathlib import Path
import csv
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
CASES={case['caso']:case for case in json.loads((ROOT/'casos_etapa7.json').read_text())}


def parse(path):
    raw=path.read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',text,re.M)
    if len(steps)!=(48 if 'validacao' in path.name else 3):
        raise RuntimeError('Quantidade de passos inesperada ou simulacao incompleta.')
    measures={}
    for name,block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',text,re.S):
        measures[name]={int(index):float(value) for index,value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',block,re.M)}
    required=[f'{name}_{index:02}' for index in range(17) for name in ('minimo','maximo','media','positivo')]+['pico_orcamento']
    if any(len(measures.get(name,{}))!=len(steps) for name in required):
        raise RuntimeError('Medidas incompletas: '+path.name)
    rows=[]
    for step,line in enumerate(steps,1):
        params={name:float(value) for name,value in re.findall(r'(\w+)=([-+\d.eE]+)',line)}
        config=CASES[int(params['caso'])] if 'caso' in params else {'caso':-1,'perfil':1,'politica':int(params['politica']),'x_inicial':0.37,'y_inicial':-0.2,'passo_tempo_us':5}
        for index,code in enumerate(SEQUENCE):
            row={'arquivo':path.name,'passo':step,**config,'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for name in ('minimo','maximo','media','positivo'):
                row[name]=measures[f'{name}_{index:02}'][step]
            row['pico_orcamento_uA']=measures['pico_orcamento'][step]*1e6
            # Tolerancia explicita de 0,005 uA para as medidas numericas.
            # Os picos observados sao preservados, inclusive valores acima de 100.
            if row['pico_orcamento_uA']>100.005:
                raise RuntimeError('Orcamento maximo ultrapassado.')
            row['margem']=row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente']=int(row['margem']>0)
            rows.append(row)
    return rows


rows=[row for filename in sys.argv[1:] for row in parse(ROOT/filename)]
if not rows:
    raise SystemExit('Informe os logs concluidos.')
with (ROOT/'resultados_etapa7.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
summary=[]
for filename,profile,policy in sorted(set((row['arquivo'],row['perfil'],row['politica']) for row in rows)):
    subset=[row for row in rows if (row['arquivo'],row['perfil'],row['politica'])==(filename,profile,policy)]
    steps=set(row['passo'] for row in subset)
    summary.append({'arquivo':filename,'perfil':profile,'politica':policy,'execucoes':len(steps),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in steps),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'menor_margem':min(row['margem'] for row in subset),'pico_orcamento_uA':max(row['pico_orcamento_uA'] for row in subset),'falhas':[{'passo':row['passo'],'janela':row['janela'],'margem':row['margem']} for row in subset if not row['acerto_persistente']]})
(ROOT/'resumo_etapa7.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in item.items() if key!='falhas'} for item in summary],indent=2,ensure_ascii=False))
