"""Le medidas do LTspice e verifica persistencia em janelas inteiras."""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEQUENCE = [0, 0, 1, 0, 2, 0, 3, 1, 1, 2, 1, 3, 2, 2, 3, 3, 0]


def parse(path):
    raw = path.read_bytes()
    text = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8', errors='replace')
    steps = re.findall(r'^\.step (.+)$', text, re.M) or ['x_inicial=0 desvio=0 passo=5e-6']
    measures = {}
    for name, block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)', text, re.S):
        measures[name] = {int(index): float(value) for index, value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)', block, re.M)}
    if len(steps) > 1:
        values = [[measures.get(f'{kind}_{index:02}', {}).get(step) for kind in ('media','minimo','maximo','positivo')] for step in range(1, len(steps)+1) for index in range(17)]
        if any(None in row for row in values):
            raise RuntimeError('Medidas ausentes; simulacao incompleta: ' + path.name)
    rows = []
    sequence=list(reversed(SEQUENCE)) if 'verificacao_nova' in path.name else SEQUENCE
    for step, line in enumerate(steps, 1):
        params = dict((name, float(value)) for name, value in re.findall(r'(\w+)=([-+\d.eE]+)', line))
        if path.name in ('MLC_AND_pilar_demo.log','MLC_AND_pilar_demo_v2.log'):
            params.update(desvio=0.005,erro_sensor=0.0002)
        if 'caso' in params:
            case=int(params['caso'])
            if 'verificacao_nova' in path.name:
                params.update(x_inicial=(-0.37,0.37)[case%2],y_inicial=-0.2,desvio=(-0.0037,0.0037)[(case//2)%2],passo=1.25e-6,erro_sensor=(-0.000137,0.000137)[case//4],controle=1)
            else:
                params.update(x_inicial=(-1,0,1)[case%3], desvio=(-0.005,0,0.005)[(case//3)%3], passo=(5e-6,2.5e-6)[(case//9)%2], erro_sensor=(-0.0002,0,0.0002)[case//18], controle=1)
        for index, code in enumerate(sequence):
            row = {'arquivo':path.name,'passo':step,'x_inicial':params.get('x_inicial',0),'y_inicial':params.get('y_inicial',0),'desvio':params.get('desvio',0),'passo_tempo':params.get('passo',5e-6),'erro_sensor':params.get('erro_sensor',0),'controle':params.get('controle',0),'janela':index,'A':code//2,'B':code%2,'esperado':int(code==3)}
            for kind in ('media','minimo','maximo','positivo'):
                name = f'{kind}_{index:02}'
                if len(steps) > 1:
                    row[kind] = measures[name][step]
                else:
                    result = re.search(rf'^{name}:.*?=\s*([-+\d.eE]+)',text,re.M|re.I)
                    if not result:
                        raise RuntimeError('Medida ausente: ' + name)
                    row[kind] = float(result.group(1))
            row['margem'] = row['minimo'] if code==3 else -row['maximo']
            row['acerto_persistente'] = int(row['margem']>0)
            rows.append(row)
    return rows


rows = [row for filename in sys.argv[1:] for row in parse(ROOT/filename)]
if not rows:
    raise SystemExit('Informe os nomes dos logs a analisar.')
with (ROOT/'MLC_resultados.csv').open('w',newline='',encoding='utf-8-sig') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
summary=[]
for filename in sorted(set(row['arquivo'] for row in rows)):
    subset=[row for row in rows if row['arquivo']==filename]
    trajectories = sorted(set(row['passo'] for row in subset))
    summary.append({'arquivo':filename,'execucoes':len(trajectories),'janelas':len(subset),'janelas_corretas':sum(row['acerto_persistente'] for row in subset),'execucoes_totalmente_corretas':sum(all(row['acerto_persistente'] for row in subset if row['passo']==step) for step in trajectories),'menor_margem':min(row['margem'] for row in subset),'falhas':[row for row in subset if not row['acerto_persistente']]})
(ROOT/'MLC_resumo.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps([{key:value for key,value in item.items() if key!='falhas'} for item in summary],indent=2,ensure_ascii=False))
