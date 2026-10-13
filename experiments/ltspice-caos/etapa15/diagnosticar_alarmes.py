"""Evidencia local dos alarmes saudaveis, sem reajustar o circuito."""
from pathlib import Path
import csv
import json
import numpy as np
from analisar_etapa15 import raw_steps

ROOT=Path(__file__).resolve().parent

def main():
    name='EXP_p3_f0_d1'
    cases=json.loads((ROOT/f'{name}.json').read_text())
    events=[]
    for i,(time,c) in enumerate(raw_steps(ROOT/f'{name}.raw',4)):
        alarm=c['v(trip)']>.5
        if not alarm.any():continue
        index=np.flatnonzero(alarm)[0]
        t0=float(time[index]);mask=(time>=t0-50e-6)&(time<=t0+50e-6)
        before=(time>=t0-20e-6)&(time<=t0)
        command_error=sum(np.abs(c[f'v(comando_{ch})'].astype(float)-c[f'v(esperado_{ch})'].astype(float)) for ch in ['y','d'])
        total_measured=sum(np.abs(c[f'v(med_{ch})'].astype(float)) for ch in ['y','d'])
        total_reference=sum(np.abs(c[f'v(esperado_{ch})'].astype(float)) for ch in ['y','d'])
        fields=['tempo_s','relativo_us','ganho_limitador','comando_erro_uA','referencia_modulos_uA','medida_modulos_uA','discrepancia_filtrada_uA','limiar_uA','timer','trip']
        values=[time,(time-t0)*1e6,c['v(ganho_fisico)'],command_error*1e6,total_reference*1e6,total_measured*1e6,c['v(discrepancia)']*100,c['v(limiar)']*100,c['v(timer)'],c['v(trip)']]
        with (ROOT/f'alarme_saudavel_caso{i}.csv').open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.writer(stream);writer.writerow(fields);writer.writerows(zip(*(v[mask] for v in values)))
        events.append(dict(caso=i,passo=cases[i]['passo'],x_inicial=cases[i]['x_inicial'],alarme_s=t0,
                           ganho_no_alarme=float(c['v(ganho_fisico)'][index]),
                           ganho_min_20us_antes=float(c['v(ganho_fisico)'][before].min()),
                           erro_comando_max_20us_uA=float(command_error[before].max())*1e6,
                           discrepancia_no_alarme_uA=float(c['v(discrepancia)'][index])*100,
                           limiar_no_alarme_uA=float(c['v(limiar)'][index])*100,
                           medida_no_alarme_uA=float(total_measured[index])*1e6,
                           referencia_instantanea_no_alarme_uA=float(total_reference[index])*1e6))
    (ROOT/'alarmes_saudaveis.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    print(json.dumps(events,indent=2))

if __name__=='__main__':main()
