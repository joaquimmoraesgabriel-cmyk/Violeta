"""Localiza divergencias entre sonda 0 V e shunt, sem descartar amostras."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
T=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
worst=max(T,key=lambda r:r['pico_sondas_uA'])
name=worst['arquivo'];cases=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
for case,(t,c) in enumerate(raw_steps(ROOT/f'{name}.raw',len(cases),max_last_gaps=[r['passo'] for r in cases])):
    if case!=worst['caso']:continue
    resistors={ch:c[f'i(x{ch}:rshunt)'].astype(float)*1e6 for ch in ['y','d','e']}
    probes={ch:c[f'i(vsense{ch})'].astype(float)*1e6 for ch in ['y','d','e']}
    voltage={ch:(c[f'v(x{ch}:entrada_shunt)'].astype(float)-c[f'v(br_{ch})'].astype(float))*1000 for ch in ['y','d','e']}
    pr=sum(abs(a) for a in probes.values());res=sum(abs(a) for a in resistors.values());volt=sum(abs(a) for a in voltage.values())
    selected={'pico_sonda':int(np.argmax(pr)),'maior_divergencia_sonda_shunt':int(np.argmax(abs(pr-volt)))}
    result=dict(arquivo=name,caso=case,passo_maximo_s=worst['passo'],pontos={})
    for label,index in selected.items():
        points=[]
        for j in range(max(0,index-2),min(len(t),index+3)):
            points.append(dict(indice=j,t_s=float(t[j]),dt_anterior_s=float(t[j]-t[j-1]) if j else None,
                soma_sondas_uA=float(pr[j]),soma_resistores_uA=float(res[j]),soma_tensoes_uA=float(volt[j]),
                sondas_uA={ch:float(v[j]) for ch,v in probes.items()},
                resistores_uA={ch:float(v[j]) for ch,v in resistors.items()}))
        result['pontos'][label]=points
    (ROOT/'diagnostico_pico_sondas.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    break
