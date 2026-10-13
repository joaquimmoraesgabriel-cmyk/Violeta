"""Auditoria independente de correntes e metricas identicas para antigos/novos RAWs."""
from pathlib import Path
import csv, hashlib, json, re, sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import measurements,raw_steps,correct_windows

def analyze(folder,name):
    cases=json.loads((folder/f'{name}.json').read_text(encoding='utf-8'))
    m=measurements(folder/f'{name}.log',len(cases))
    rawlog=(folder/f'{name}.log').read_bytes()
    log=rawlog.decode('utf-16' if rawlog.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    if re.search(r'tolerance relaxed|time step too small|singular matrix',log,re.I):
        raise ValueError(f'{name}: aviso numerico requer auditoria')
    ts,rows=[],[]
    for index,(time,c) in enumerate(raw_steps(folder/f'{name}.raw',len(cases),max_last_gaps=[p['passo'] for p in cases])):
        p=cases[index]
        margins,correct=correct_windows(m,index+1)
        has_e='v(xe:entrada_shunt)' in c
        channels=['y','d']+(['e'] if has_e else [])
        act={ch:(c[f'v(x{ch}:entrada_shunt)'].astype(float)-c[f'v(br_{ch})'].astype(float))/1000 for ch in channels}
        physical=sum(np.abs(v) for v in act.values())
        resistor=sum(np.abs(c[f'i(x{ch}:rshunt)'].astype(float)) for ch in channels)
        probe=sum(np.abs(c[f'i(vsense{ch})'].astype(float)) for ch in channels)
        measured=sum(np.abs(c[f'v(med_{ch})'].astype(float)) for ch in channels)
        for a in [time,*c.values(),physical,probe,resistor]:
            if not np.isfinite(a).all():raise ValueError(f'{name}: valores nao finitos')
        alarm=c['v(trip)']>.5
        reserve=c['v(reserva_ativa)']>.5
        fault=p['falha_coord']; start=0 if fault==2 else .34335
        before=(time>=.002) & ((time<start) if fault else True)
        hits=time[alarm & (time>=start)]
        x=c['v(x)'].astype(float); y=c['v(y)'].astype(float)
        g=-.55*x+(-1.02+.55)/2*(np.abs(x+1)-np.abs(x-1))
        pa=p['amp_a']*np.sin(2*np.pi*500*time)
        pb=p['amp_b']*np.sin(2*np.pi*137*time+np.deg2rad(40))
        pc=p['amp_c']*np.sin(2*np.pi*73*time+np.deg2rad(65))
        pd=p['amp_d']*np.sin(2*np.pi*211*time+np.deg2rad(17))
        desired_d=.01*pd*g
        desired_y=.01*(1.015*pa*y-pb-pc*np.sin(.74*time/100e-6))
        e=act['e'] if has_e else np.zeros(len(time))
        residual_d=(act['d']+e-desired_d)*1e6
        residual_y=(act['y']-desired_y)*1e6
        mask=time>=.03; t=time[mask]; duration=t[-1]-t[0]
        # Indicadores booleanos precisam virar 0/1 antes da soma trapezoidal.
        def mean(a):return float(np.trapezoid(np.asarray(a,dtype=float)[mask],t)/duration)
        def rms(a):return np.sqrt(mean(np.asarray(a)**2)).item()
        trow=dict(arquivo=name,origem=folder.name,**p,corretas=sum(correct),margem_minima=min(margins),
            ultimo_tempo_raw_s=float(time[-1]),lacuna_final_us=float(max(0,.85-time[-1])*1e6),
            pico_tensoes_uA=float(physical.max()*1e6),pico_resistores_uA=float(resistor.max()*1e6),
            pico_sondas_uA=float(probe.max()*1e6),pico_medidor_uA=float(measured.max()*1e6),
            diferenca_resistores_uA=float(np.max(np.abs(physical-resistor))*1e6),
            diferenca_sondas_uA=float(np.max(np.abs(physical-probe))*1e6),
            diferenca_medidor_uA=float(np.max(np.abs(physical-measured))*1e6),
            corrente_falha=bool(physical.max()>100.005e-6),
            corrente_falha_resistores=bool(resistor.max()>100.005e-6),
            corrente_falha_sondas=bool(probe.max()>100.005e-6),
            alarme_indevido=bool(np.any(alarm & before)),reserva_indevida=bool(np.any(reserve & before)),
            latencia_alarme_us=float((hits[0]-start)*1e6) if fault and len(hits) else None,
            reserva_retida=bool(reserve[-1]),rms_residuo_d_uA=rms(residual_d),
            pico_residuo_d_uA=float(np.max(np.abs(residual_d[mask]))),rms_residuo_y_uA=rms(residual_y),
            rms_g=rms(g),pico_g=float(np.max(np.abs(g[mask]))),variacao_g_por_s=float(np.abs(np.diff(g[mask])).sum()/duration),
            fracao_fora_quebras=mean(np.abs(x)>1),media_modulo_d_uA=mean(np.abs(act['d'])*1e6),
            media_modulo_e_uA=mean(np.abs(e)*1e6),pico_e_uA=float(np.max(np.abs(e))*1e6),
            fracao_e=mean(np.abs(e)>1e-6),fracao_limitador=mean(c['v(ganho_fisico)']<.999),
            fracao_demanda_real_acima_90=mean(np.abs(desired_d)+np.abs(desired_y)>91e-6),
            media_excesso_demanda_real_uA=mean(np.maximum(0,np.abs(desired_d)+np.abs(desired_y)-90e-6)*1e6),
            janelas_falhas=[i for i,a in enumerate(correct) if not a])
        if has_e:
            expected=c['v(esperado_e)'].astype(float)
            demand=c['v(demanda_d)'].astype(float); base=c['v(base_d)'].astype(float)
            trow['e_sem_saturacao']=bool(np.any((np.abs(expected)>1e-9)&(np.abs(demand)<np.abs(base)+.999e-6)))
            trow['e_contrario_d']=bool(np.any(expected*demand < -1e-18))
            trow['pico_comando_e_uA']=float(np.max(np.abs(expected))*1e6)
            trow['erro_mediana_e_max']=float(np.max(np.abs(c['v(estimativa_e)'].astype(float)-(pd+.00002*p.get('esc_erro',1)+p.get('erro_comum_e',0)))))
            trow['rms_erro_sensor_e']=rms(c['v(estimativa_e)'].astype(float)-pd)
        ts.append(trow)
        rows += [dict(arquivo=name,origem=folder.name,caso=index,falha_coord=fault,x_inicial=p['x_inicial'],passo=p['passo'],janela=j,acerto=v,margem=margins[j]) for j,v in enumerate(correct)]
    return ts,rows

def summarize(ts,rs):
    groups=[]
    for name in dict.fromkeys(t['arquivo'] for t in ts):
        part=[t for t in ts if t['arquivo']==name]; rows=[r for r in rs if r['arquivo']==name]
        by_step={s:{(r['x_inicial'],r['janela']):r['acerto'] for r in rows if r['passo']==s} for s in sorted({t['passo'] for t in part},reverse=True)}
        pairs=[]
        for sa,sb in zip(list(by_step)[:-1],list(by_step)[1:]):
            a,b=by_step[sa],by_step[sb]; assert a.keys()==b.keys()
            pairs.append(dict(passos_us=[sa*1e6,sb*1e6],acertos_ambos=sum(a[k] and b[k] for k in a),divergencias=sum(a[k]!=b[k] for k in a)))
        row=dict(arquivo=name,trajetorias=len(part),corretas=sum(t['corretas'] for t in part),janelas=len(rows),
                 por_passo={str(s):sum(v.values()) for s,v in by_step.items()},pares=pairs,
                 inteiras=sum(t['corretas']==17 for t in part),alarmes_indevidos=sum(t['alarme_indevido'] for t in part),
                 falhas_corrente=sum(t['corrente_falha'] for t in part),pico_corrente_uA=max(t['pico_tensoes_uA'] for t in part))
        for metric in ['rms_residuo_d_uA','rms_residuo_y_uA','rms_g','variacao_g_por_s','fracao_fora_quebras','media_modulo_d_uA','media_modulo_e_uA','fracao_e']:
            row[metric]=sum(t[metric] for t in part)/len(part)
        groups.append(row)
    return groups

def main(partial=False):
    ts=[];rows=[];pending=[]
    specs=[(ROOT.parent/'etapa15',f'BUF_p3_f{f}') for f in [0,4,2,3]]
    for manifest in sorted(ROOT.glob('lotes_*.json')):
        specs += [(ROOT,name) for name in json.loads(manifest.read_text(encoding='utf-8'))]
    specs=list(dict.fromkeys(specs))
    cache=ROOT/'cache_analise';cache.mkdir(exist_ok=True)
    codehash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for folder,name in specs:
        try:
            signature=[codehash]+[(folder/f'{name}{ext}').stat().st_mtime_ns for ext in ['.cir','.json','.log','.raw']]
            cached=cache/f'{folder.name}_{name}.json'
            data=json.loads(cached.read_text(encoding='utf-8')) if cached.exists() else {}
            if data.get('signature')==signature:a,b=data['trajectories'],data['rows']
            else:
                a,b=analyze(folder,name)
                cached.write_text(json.dumps(dict(signature=signature,trajectories=a,rows=b)),encoding='utf-8')
        except (FileNotFoundError,ValueError) as e:
            if not partial:raise
            pending.append(str(e));continue
        ts+=a;rows+=b
    summary=summarize(ts,rows)
    suffix='_parcial' if partial else ''
    for fname,data in [('trajetorias',ts),('resumo',summary)]:
        (ROOT/f'{fname}{suffix}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    with (ROOT/f'janelas{suffix}.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    if '--compact' in sys.argv:
        for s in summary:
            print(f"{s['arquivo']}: {s['corretas']}/{s['janelas']}, pares={s['pares']}, RD={s['rms_residuo_d_uA']:.3f}, RY={s['rms_residuo_y_uA']:.3f}, falsos={s['alarmes_indevidos']}, corrente={s['pico_corrente_uA']:.5f}")
        print(f"Novas={sum(t['origem']=='etapa16' for t in ts)}, referencia={sum(t['origem']=='etapa15' for t in ts)}, pendentes={len(pending)}")
    else:print(json.dumps(dict(novas=sum(t['origem']=='etapa16' for t in ts),referencia=sum(t['origem']=='etapa15' for t in ts),pendentes=pending,resumo=summary),indent=2))

if __name__=='__main__':main('--partial' in sys.argv)
