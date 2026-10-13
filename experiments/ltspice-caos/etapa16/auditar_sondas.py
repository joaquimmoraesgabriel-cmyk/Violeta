"""Localiza as divergencias pontuais entre sondas de 0 V e correntes pelos shunts."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
allts=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
selected=sorted([t for t in allts if t['origem']=='etapa16'],key=lambda t:t['diferenca_sondas_uA'],reverse=True)[:2]
result=[]
for meta in selected:
    name=meta['arquivo'];cases=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
    for case,(time,c) in enumerate(raw_steps(ROOT/f'{name}.raw',len(cases))):
        if case!=meta['caso']:continue
        channels=['y','d']+(['e'] if 'v(med_e)' in c else [])
        actual={ch:(c[f'v(x{ch}:entrada_shunt)'].astype(float)-c[f'v(br_{ch})'].astype(float))/1000 for ch in channels}
        resistor={ch:c[f'i(x{ch}:rshunt)'].astype(float) for ch in channels}
        probes={ch:c[f'i(vsense{ch})'].astype(float) for ch in channels}
        diff=sum(np.abs(v) for v in actual.values())-sum(np.abs(v) for v in probes.values())
        k=int(np.argmax(np.abs(diff)))
        event=dict(arquivo=name,caso=case,tempo_s=float(time[k]),x_V=float(c['v(x)'][k]),
                   dt_anterior_s=float(time[k]-time[k-1]),dt_seguinte_s=float(time[k+1]-time[k]),
                   diferenca_total_uA=float(diff[k]*1e6),
                   rms_diferenca_uA=float(np.sqrt(np.trapezoid(diff**2,time)/.85)*1e6),
                   tempo_diferenca_acima_1uA_us=float(np.trapezoid((np.abs(diff)>1e-6).astype(float),time)*1e6),
                   picos_uA=dict(shunts=meta['pico_tensoes_uA'],resistores=meta['pico_resistores_uA'],sondas=meta['pico_sondas_uA']),
                   amostras=[])
        for j in range(max(0,k-2),min(len(time),k+3)):
            event['amostras'].append(dict(t=float(time[j]),correntes_uA={ch:dict(shunt=float(actual[ch][j]*1e6),resistor=float(resistor[ch][j]*1e6),sonda=float(probes[ch][j]*1e6)) for ch in channels}))
        result.append(event)
(ROOT/'auditoria_sondas.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in e.items() if k!='amostras'} for e in result],indent=2))
