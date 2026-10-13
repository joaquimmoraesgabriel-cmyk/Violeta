"""Verifica logs completos, classifica janelas e audita tres leituras de corrente."""
from pathlib import Path
import csv
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa12'))
from leitura_independente import measurements, raw_steps, current_sum, correct_windows

def analyze(name):
    cases = json.loads((ROOT / f'{name}.json').read_text())
    m = measurements(ROOT / f'{name}.log', len(cases))
    ts, rows = [], []
    for i, (time, c) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases))):
        case = cases[i]
        margins, ok = correct_windows(m, i+1)
        direct = [((c[f'v({sub}:entrada_shunt)'].astype(float) - c[f'v(br_{ch})'].astype(float))/1000)
                  for sub, ch in [('xy', 'y'), ('xd', 'd')]]
        physical = sum(np.abs(a) for a in direct)
        probe = current_sum(c, 'i(vsense')
        resistor = sum(np.abs(c[f'i({sub}:rshunt)'].astype(float)) for sub in ['xy', 'xd'])
        measured = sum(np.abs(c[f'v(med_{ch})'].astype(float)) for ch in ['y', 'd'])
        for a in [time, physical, probe, resistor, measured]:
            if not np.all(np.isfinite(a)):
                raise ValueError(f'{name}: valores nao finitos')
        alarm, reserve = c['v(trip)'] > .5, c['v(reserva_ativa)'] > .5
        fault = case['falha_coord']
        start = 0 if fault == 2 else .34335
        valid = time >= .002
        before = valid if fault == 0 else valid & (time < start)
        hits = time[alarm & (time >= start)]
        rhits = time[reserve & (time >= start)]
        t = dict(arquivo=name, **case, corretas=sum(ok), margem_minima=min(margins),
                 pico_tensoes_uA=float(physical.max())*1e6, pico_sondas_uA=float(probe.max())*1e6,
                 pico_resistores_uA=float(resistor.max())*1e6, pico_medidor_uA=float(measured.max())*1e6,
                 diferenca_sondas_uA=float(np.max(np.abs(physical-probe)))*1e6,
                 diferenca_resistores_uA=float(np.max(np.abs(physical-resistor)))*1e6,
                 diferenca_medidor_uA=float(np.max(np.abs(physical-measured)))*1e6,
                 corrente_falha_tensoes=bool(physical.max()>100.005e-6),
                 corrente_falha_sondas=bool(probe.max()>100.005e-6),
                 corrente_falha_resistores=bool(resistor.max()>100.005e-6),
                 alarme_indevido=bool(np.any(alarm & before)),
                 reserva_indevida=bool(np.any(reserve & before)),
                 primeiro_alarme_s=float(time[np.flatnonzero(alarm)[0]]) if alarm.any() else None,
                 latencia_alarme_us=float((hits[0]-start)*1e6) if fault and len(hits) else None,
                 latencia_reserva_us=float((rhits[0]-start)*1e6) if fault and len(rhits) else None,
                 reserva_retida=bool(reserve[-1]),
                 fracao_falta_maior_1uA=float(np.trapezoid((c['v(falta)'] > 1e-6).astype(float),time)/.85),
                 pico_falta_uA=float(c['v(falta)'].max())*1e6,
                 fracao_limitador=float(np.trapezoid((c['v(ganho_fisico)'] < .999).astype(float),time)/.85),
                 fracao_reserva=float(np.trapezoid(reserve.astype(float),time)/.85),
                 janelas_falhas=[j for j,a in enumerate(ok) if not a])
        ts.append(t)
        rows.extend(dict(**t, janela=j, margem=margins[j], acerto=ok[j]) for j in range(17))
    return ts, rows

def main(partial=False):
    trajectories, rows, pending = [], [], []
    for name in json.loads((ROOT/'lotes.json').read_text()):
        try:
            # As medidas completas e a duracao final do RAW validam a conclusao.
            ts, rs = analyze(name)
        except (ValueError, FileNotFoundError):
            if not partial: raise
            pending.append(name)
            continue
        trajectories.extend(ts)
        rows.extend(rs)
    summaries = []
    for key in sorted({(t['perfil'],t['falha_coord'],t['detector']) for t in trajectories}):
        ts = [t for t in trajectories if (t['perfil'],t['falha_coord'],t['detector']) == key]
        rs = [r for r in rows if (r['perfil'],r['falha_coord'],r['detector']) == key]
        by_step = {s:{(r['x_inicial'],r['janela']):r['acerto'] for r in rs if r['passo']==s} for s in sorted({t['passo'] for t in ts})}
        paired = changes = None
        if len(by_step)==2:
            a,b=by_step.values()
            assert a.keys()==b.keys()
            paired=sum(a[k] and b[k] for k in a)
            changes=sum(a[k]!=b[k] for k in a)
        latency=[t['latencia_alarme_us'] for t in ts if t['latencia_alarme_us'] is not None]
        summaries.append(dict(perfil=key[0], falha=key[1], detector=key[2], trajetorias=len(ts),
                              corretas=sum(t['corretas'] for t in ts), janelas=len(rs),
                              corretas_ambos_passos=paired, divergencias_passos=changes,
                              inteiras=sum(t['corretas']==17 for t in ts),
                              pico_tensoes_uA=max(t['pico_tensoes_uA'] for t in ts),
                              alarmes_indevidos=sum(t['alarme_indevido'] for t in ts),
                              latencia_min_us=min(latency) if latency else None,
                              latencia_max_us=max(latency) if latency else None,
                              acertos_por_passo={str(s):sum(v.values()) for s,v in by_step.items()}))
    suffix='_parcial' if partial else ''
    for filename,data in [('trajetorias',trajectories),('resumo',summaries)]:
        (ROOT/f'{filename}{suffix}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    if rows:
        with (ROOT/f'resultados{suffix}.csv').open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(dict(trajetorias=len(trajectories), janelas=len(rows), pendentes=pending, resumo=summaries),indent=2))

if __name__=='__main__':
    main('--partial' in sys.argv)
