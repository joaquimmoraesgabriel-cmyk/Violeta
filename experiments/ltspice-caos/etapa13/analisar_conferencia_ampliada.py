"""Medidas completas, somas de corrente externas e comparacao pareada."""
from pathlib import Path
import csv
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa12'))
from leitura_independente import measurements, raw_steps, current_sum, correct_windows

rows = []
trajectories = []
jobs = json.loads((ROOT / 'lotes_ampliados.json').read_text())
for name in jobs:
    cases = json.loads((ROOT / f'{name}.json').read_text())
    m = measurements(ROOT / f'{name}.log', len(cases))
    for i, (times, columns) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases))):
        c = cases[i]
        margins, correct = correct_windows(m, i + 1)
        actual = current_sum(columns, 'i(vsense')
        architecture = 'combinados' if '_combinados_' in name else 'separados'
        t = {'arquivo': name, **c, 'arquitetura': architecture, 'corretas': sum(correct), 'margem_minima': min(margins),
             'pico_monitor_uA': m['pico_orcamento'][i + 1] * 1e6, 'pico_correntes_uA': float(actual.max()) * 1e6,
             'fora_tolerancia_correntes': int(actual.max() > 100.005e-6),
             'max_discrepancia_monitor_uA': float(np.max(np.abs(actual - columns['v(orcamento)'].astype(np.float64)))) * 1e6}
        for metric in ['cancelamento_medio', 'cancelamento_maximo', 'pedido_separado_medio', 'pedido_liquido_medio']:
            if set(m.get(metric, {})) != set(range(1, len(cases) + 1)):
                raise ValueError(f'{name}: {metric} incompleto')
            t[metric + '_uA'] = m[metric][i + 1] * 1e6
        trajectories.append(t)
        for j in range(17):
            rows.append({**t, 'janela': j, 'margem': margins[j], 'acerto': correct[j]})

with (ROOT / 'resultados_ampliados.csv').open('w', newline='', encoding='utf-8-sig') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(ROOT / 'trajetorias_ampliadas.json').write_text(json.dumps(trajectories, indent=2), encoding='utf-8')

summary = []
for architecture in ['separados', 'combinados']:
    for fault in range(5):
        profiles = range(4) if fault == 0 else [1]
        for profile in profiles:
            selected = [r for r in rows if r['arquitetura'] == architecture and r['falha_coord'] == fault and r['perfil'] == profile]
            ts = [t for t in trajectories if t['arquitetura'] == architecture and t['falha_coord'] == fault and t['perfil'] == profile]
            bystep = {step: [r for r in selected if r['passo'] == step] for step in [2.5e-6, 1.25e-6]}
            lookup = [{(r['x_inicial'], r['janela']): r for r in bystep[step]} for step in [2.5e-6, 1.25e-6]]
            if len(selected) != 68 or len(ts) != 4 or any(len(v) != 34 for v in lookup):
                raise ValueError('Grupo incompleto')
            summary.append({'arquitetura': architecture, 'perfil': profile, 'falha': fault,
                            'corretas': sum(r['acerto'] for r in selected), 'janelas': len(selected),
                            'corretas_passo_2_5': sum(r['acerto'] for r in bystep[2.5e-6]),
                            'corretas_passo_1_25': sum(r['acerto'] for r in bystep[1.25e-6]),
                            'corretas_ambos_passos': sum(all(v[key]['acerto'] for v in lookup) for key in lookup[0]),
                            'classificacoes_alteradas': sum(lookup[0][key]['acerto'] != lookup[1][key]['acerto'] for key in lookup[0]),
                            'trajetorias_inteiras': sum(t['corretas'] == 17 for t in ts),
                            'pico_correntes_uA': max(t['pico_correntes_uA'] for t in ts),
                            'fora_tolerancia_correntes': sum(t['fora_tolerancia_correntes'] for t in ts),
                            'cancelamento_medio_uA': sum(t['cancelamento_medio_uA'] for t in ts) / len(ts)})
(ROOT / 'resumo_ampliado.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
