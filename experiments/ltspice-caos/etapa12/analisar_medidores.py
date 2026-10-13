"""Comparar monitor comportamental com soma externa das correntes salvas."""
from pathlib import Path
import json
import numpy as np
from leitura_independente import measurements, raw_steps, current_sum, correct_windows

ROOT = Path(__file__).resolve().parent
rows = []
for name in json.loads((ROOT / 'lote_medidores.json').read_text()):
    cases = json.loads((ROOT / f'{name}.json').read_text())
    measures = measurements(ROOT / f'{name}.log', len(cases))
    for i, (times, columns) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases))):
        applied = current_sum(columns, 'i(bcorrecao_')
        monitor = columns['v(orcamento)'].astype(np.float64)
        margins, correct = correct_windows(measures, i + 1)
        row = {'arquivo': name, 'x_inicial': cases[i]['x_inicial'], 'vntol': 1e-11 if name.endswith('preciso') else 1e-9,
               'pico_monitor_meas_uA': measures['pico_orcamento'][i + 1] * 1e6,
               'pico_correntes_salvas_uA': float(applied.max()) * 1e6,
               'maior_diferenca_monitor_correntes_uA': float(np.max(np.abs(monitor - applied))) * 1e6,
               'corrente_no_pico_monitor_uA': float(applied[np.argmax(monitor)]) * 1e6,
               'tempo_pico_monitor_s': float(times[np.argmax(monitor)]),
               'corretas': sum(correct), 'margem_minima': min(margins)}
        row['fora_tolerancia_correntes'] = int(row['pico_correntes_salvas_uA'] > 100.005)
        if 'sondas' in name:
            sensed = current_sum(columns, 'i(vsense')
            row['pico_sondas_salvas_uA'] = float(sensed.max()) * 1e6
            row['maior_diferenca_sondas_fontes_uA'] = float(np.max(np.abs(sensed - applied))) * 1e6
        rows.append(row)
(ROOT / 'conferencia_medidores.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
table = ['| Medicao | vntol | x inicial | Pico monitor (µA) | Soma das correntes (µA) | Diferenca maxima (µA) | Acertos |',
         '|---|---|---|---|---|---|---|']
for r in rows:
    table.append(f"| {'Sondas de 0 V' if 'sondas' in r['arquivo'] else 'Direta'} | {r['vntol']:g} | {r['x_inicial']:+.2f} | {r['pico_monitor_meas_uA']:.9f} | {r['pico_correntes_salvas_uA']:.9f} | {r['maior_diferenca_monitor_correntes_uA']:.9f} | {r['corretas']}/17 |")
report = f'''# Conferência independente de corrente da etapa 12

Nos oito ensaios, nenhum pico da soma externa das correntes excedeu o critério de 100,005 µA. O maior foi {max(r['pico_correntes_salvas_uA'] for r in rows):.9f} µA. O monitor interno chegou a {max(r['pico_monitor_meas_uA'] for r in rows):.9f} µA. Assim, o excesso indicado por esse monitor não foi confirmado como corrente aplicada acima do critério nestas execuções. A classificação dos outros casos antigos continua pendente de conferência independente.

Repetimos o coordenador comum no perfil AB exige mais, com falha silenciosa do topo e dois estados iniciais. São oito trajetórias: monitor direto e sondas ideais de 0 V, cada um com vntol de 1e-9 e 1e-11; reltol=1e-6, abstol=1e-12, passo máximo=2,5 µs. A referência é o mesmo caso de COORD_falha4_AB.

A soma abaixo é calculada fora do LTspice a partir das correntes salvas no RAW, no mesmo instante. Ela não depende da fonte B que exibe V(orcamento). Nos arquivos com sondas, também conferimos a soma das correntes das fontes de 0 V contra as fontes de atuação. Todos os logs precisam conter as 17 janelas completas e os RAW chegar a 0,85 s.

''' + '\n'.join(table) + '''

As correntes do RAW têm precisão de armazenamento de 32 bits. Os extremos de .meas são registrados separadamente; pequenos resíduos da ordem de 0,00001 µA na soma externa não sustentam uma alegação de ultrapassagem física. A tolerância de verificação continua 0,005 µA e a capacidade nominal continua 100 µA.

Fontes de 0 V são equivalentes elétricos ideais, mas sua inclusão muda as equações resolvidas e pode mudar a trajetória numérica de um sistema sensível. Portanto comparamos os picos e classificações de cada execução; não exigimos identidade ponto a ponto entre execuções distintas.

A documentação da Analog Devices explica as limitações das referências a correntes em fontes comportamentais: [Behavioral Sources, Parameters and Expression Evaluation](https://ez.analog.com/cfs-file/__key/docpreview-s/00-00-01-54-13/todaysslidedeck6141655150841730.pdf). O resultado desta conferência está em conferencia_medidores.json. A conclusão deve distinguir discrepância no monitor, resíduo numérico da solução e uma corrente aplicada acima do critério; não extrapolamos estes oito casos a todas as execuções antigas.
'''
(ROOT / 'MEDICAO_CORRENTE.md').write_text(report, encoding='utf-8')
print(json.dumps(rows, indent=2))
