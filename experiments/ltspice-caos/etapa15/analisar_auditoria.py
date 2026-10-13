"""Localiza em qual interface aparece o erro que dispara o detector saudavel."""
from pathlib import Path
import json
import csv
import sys
import numpy as np
from analisar_etapa15 import analyze,raw_steps

ROOT=Path(__file__).resolve().parent

def main():
    rows=[]
    names=sys.argv[1:] or ['AUD_circuito','AUD_ideal90']
    for name in names:
        ts,_=analyze(name)
        for i,(time,c) in enumerate(raw_steps(ROOT/f'{name}.raw',2)):
            rows.append(diagnose(name,i,time,c,ts[i]))
    output='auditoria_diagnostico_parcial.json' if sys.argv[1:] else 'auditoria_diagnostico.json'
    (ROOT/output).write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k!='trajetoria'} for r in rows],indent=2))

def diagnose(name,i,time,c,trajectory):
        ids=np.flatnonzero(c['v(trip)']>.5)
        if not len(ids):
            return dict(arquivo=name,caso=i,resultado='Sem alarme nesta repeticao',trajetoria=trajectory)
        k=ids[0];t0=float(time[k]);window=(time>=t0-20e-6)&(time<=t0)
        data={key:c[key].astype(float) for key in c}
        channels={}
        for ch in ['y','d']:
            cmd=data[f'v(comando_{ch})']
            exp=data[f'v(esperado_{ch})']
            filt=data[f'v(filtro_{ch})']/10000
            exp_rc=data[f'v(exp_{ch})']/10000
            med=data[f'v(med_{ch})']
            obs_f=data[f'v(obs_{ch}_f)']/10000
            exp_f=data[f'v(exp_{ch}_f)']/10000
            channels[ch]=dict(comando_uA=cmd[k]*1e6,esperado_uA=exp[k]*1e6,
                              filtro_comando_uA=filt[k]*1e6,filtro_referencia_uA=exp_rc[k]*1e6,
                              medido_uA=med[k]*1e6,observacao_filtrada_uA=obs_f[k]*1e6,referencia_filtrada_uA=exp_f[k]*1e6,
                              erro_entrada_max_20us_uA=float(np.max(np.abs(cmd-exp)[window]))*1e6,
                              erro_RCs_max_20us_uA=float(np.max(np.abs(filt-exp_rc)[window]))*1e6,
                              erro_medida_comando_max_20us_uA=float(np.max(np.abs(med-filt)[window]))*1e6)
        fields=['time']+list(data)
        event_window=(time>=t0-100e-6)&(time<=t0+100e-6)
        with (ROOT/f'{name}_caso{i}_evento.csv').open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.writer(stream);writer.writerow(fields)
            writer.writerows(zip(time[event_window],*(v[event_window] for v in data.values())))
        return dict(arquivo=name,caso=i,primeiro_alarme_s=t0,canais=channels,trajetoria=trajectory)

if __name__=='__main__':main()
