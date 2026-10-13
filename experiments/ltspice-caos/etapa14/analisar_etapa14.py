"""Extremos logicos, correntes independentes e diagnostico causal do topo."""
from pathlib import Path
import csv
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa12'))
from leitura_independente import measurements, raw_steps, current_sum, correct_windows

def analyze(manifests):
    trajectories, rows = [], []
    for manifest in manifests:
        for name in json.loads((ROOT / manifest).read_text()):
            cases = json.loads((ROOT / f'{name}.json').read_text())
            m = measurements(ROOT / f'{name}.log', len(cases))
            for i, (time, c) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases))):
                case = cases[i]
                margins, ok = correct_windows(m, i + 1)
                current = current_sum(c, 'i(vsense')
                shunt = np.abs(c['v(med_y)'].astype(float)) + np.abs(c['v(med_d)'].astype(float))
                alarm = c['v(trip)'] > .5
                reserve = c['v(reserva_ativa)'] > .5
                start = 0 if case['falha_coord'] == 2 else .34335
                alarms_after = time[alarm & (time >= start)]
                reserves_after = time[reserve & (time >= start)]
                false = bool(np.any(alarm & (time > .002))) if case['falha_coord'] == 0 else (bool(np.any(alarm & (time > .002) & (time < start))) if start else False)
                t = {'arquivo': name, **case, 'corretas': sum(ok), 'margem_minima': min(margins),
                     'pico_correntes_uA': float(current.max()) * 1e6, 'fora_tolerancia': int(current.max() > 100.005e-6),
                     'pico_monitor_uA': m['pico_orcamento'][i + 1] * 1e6,
                     'pico_medida_shunt_uA': float(shunt.max()) * 1e6,
                     'maior_diferenca_shunt_sonda_uA': float(np.max(np.abs(current - shunt))) * 1e6,
                     'alarme_sem_falha': false,
                     'primeiro_alarme_s': float(time[np.flatnonzero(alarm)[0]]) if np.any(alarm) else None,
                     'latencia_alarme_us': float((alarms_after[0] - start) * 1e6) if case['falha_coord'] and len(alarms_after) else None,
                     'latencia_reserva_us': float((reserves_after[0] - start) * 1e6) if case['falha_coord'] and len(reserves_after) else None,
                     'fracao_reserva': float(np.trapezoid(reserve.astype(float), time) / (time[-1] - time[0]))}
                trajectories.append(t)
                rows.extend({**t, 'janela': j, 'margem': margins[j], 'acerto': ok[j]} for j in range(17))
    (ROOT / 'trajetorias.json').write_text(json.dumps(trajectories, indent=2), encoding='utf-8')
    with (ROOT / 'resultados.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for key in sorted({(t['hardware'], t['cap_operacao'], t['detector'], t['falha_coord'], t['perfil']) for t in trajectories}):
        subset = [t for t in trajectories if (t['hardware'], t['cap_operacao'], t['detector'], t['falha_coord'], t['perfil']) == key]
        rs = [r for r in rows if (r['hardware'], r['cap_operacao'], r['detector'], r['falha_coord'], r['perfil']) == key]
        latencies = [t['latencia_alarme_us'] for t in subset if t['latencia_alarme_us'] is not None]
        paired = None
        if {r['passo'] for r in rs} == {2.5e-6, 1.25e-6}:
            lookup = {s: {(r['x_inicial'], r['janela']): r['acerto'] for r in rs if r['passo'] == s} for s in [2.5e-6, 1.25e-6]}
            paired = sum(lookup[2.5e-6][k] and lookup[1.25e-6][k] for k in lookup[2.5e-6])
        summary.append(dict(zip(['hardware', 'cap_operacao', 'detector', 'falha', 'perfil'], key),
                            trajetorias=len(subset), corretas=sum(t['corretas'] for t in subset), janelas=len(subset)*17,
                            trajetorias_inteiras=sum(t['corretas'] == 17 for t in subset), corretas_ambos_passos=paired,
                            pico_correntes_uA=max(t['pico_correntes_uA'] for t in subset), fora_tolerancia=sum(t['fora_tolerancia'] for t in subset),
                            alarmes_sem_falha=sum(t['alarme_sem_falha'] for t in subset),
                            latencia_min_us=min(latencies) if latencies else None, latencia_max_us=max(latencies) if latencies else None))
    (ROOT / 'resumo.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    analyze(sys.argv[1:] or ['lotes_detector.json'])
