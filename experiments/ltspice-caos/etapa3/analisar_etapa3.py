"""Analisa medidas reais, com criterio de sinal persistente em janela inteira."""
from pathlib import Path
import csv
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
CASES={case['caso']:case for case in json.loads((ROOT/'casos_etapa3.json').read_text())}
MODES=['desligado','ideal','atrasado_limitado','mais_lento_fraco']
PROFILES=['senoide_5Hz','alternancia_25ms','senoide_500Hz']


def parse(path):
    raw=path.read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    steps=re.findall(r'^\.step (.+)$',text,re.M)
    measures={}
    for name,block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)',text,re.S):
        measures[name]={int(index):float(value) for index,value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)',block,re.M)}
    if not steps:
        raise RuntimeError('Nenhum passo no log: '+path.name)
    rows=[]
    for step,line in enumerate(steps,1):
        params={name:float(value) for name,value in re.findall(r'(\w+)=([-+\d.eE]+)',line)}
        if 'caso' in params:
            params=CASES[int(params['caso'])]
        else:
            params.update(perfil=2 if 'limite' in path.name else 1,x_inicial=0.37 if 'limite' in path.name else 0,y_inicial=-0.2,erro_sensor=0.0002,passo=5e-6,caso=-1)
        for index,code in enumerate(SEQUENCE):
            row={'arquivo':path.name,'passo':step,'caso':params['caso'],'perfil':params['perfil'],'modo':params['modo'],'x_inicial':params['x_inicial'],'y_inicial':params['y_inicial'],'erro_sensor':params['erro_sensor'],'passo_tempo':params['passo'],'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for kind in ('minimo','maximo','media','positivo','saturado','tracking'):
                row[kind]=measures[f'{kind}_{index:02}'][step]
            row['pico_corrente']=measures['pico_corrente'][step]
            row['margem']=row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente']=int(row['margem']>0)
            rows.append(row)
    return rows


rows=[row for filename in sys.argv[1:] for row in parse(ROOT/filename)]
if not rows:
    raise SystemExit('Informe os logs concluidos.')
with (ROOT/'resultados_etapa3.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
summary=[]
for filename,profile,mode in sorted(set((row['arquivo'],int(row['perfil']),int(row['modo'])) for row in rows)):
    subset=[row for row in rows if (row['arquivo'],int(row['perfil']),int(row['modo']))==(filename,profile,mode)]
    trajectories=sorted(set(row['passo'] for row in subset))
    summary.append({'arquivo':filename,'perfil':PROFILES[profile],'modo':MODES[mode],'execucoes':len(trajectories),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in trajectories),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'menor_margem':min(row['margem'] for row in subset),'pico_corrente_uA':max(row['pico_corrente'] for row in subset)*1e6,'fracao_saturada_nas_janelas':sum(row['saturado'] for row in subset)/len(subset),'tracking_rms_medio':sum(row['tracking'] for row in subset)/len(subset),'falhas':[{'passo':row['passo'],'janela':row['janela'],'A':row['A'],'B':row['B'],'margem':row['margem']} for row in subset if not row['acerto_persistente']]})
(ROOT/'resumo_etapa3.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in item.items() if key!='falhas'} for item in summary],indent=2,ensure_ascii=False))
