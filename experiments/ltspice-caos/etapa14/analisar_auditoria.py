"""Comparacao de correntes, tensoes diretas e mediadores comportamentais."""
from pathlib import Path
import json
import sys
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa12'))
from leitura_independente import measurements, raw_steps, current_sum, correct_windows

def main():
    rows = []
    for name in ['AUDIT_atraso', 'AUDIT_circuito']:
        cases = json.loads((ROOT / f'{name}.json').read_text())
        m = measurements(ROOT / f'{name}.log', len(cases))
        for i, (time, c) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases))):
            if name == 'AUDIT_atraso':
                iy = (c['v(n_y)'].astype(float) - c['v(br_y)'].astype(float)) / 1000
                ix = (c['v(n_d)'].astype(float) - c['v(br_d)'].astype(float)) / 1000
            else:
                iy = (c['v(xy:entrada_shunt)'].astype(float) - c['v(br_y)'].astype(float)) / 1000
                ix = (c['v(xd:entrada_shunt)'].astype(float) - c['v(br_d)'].astype(float)) / 1000
            voltage_sum = np.abs(iy) + np.abs(ix)
            sense_sum = current_sum(c, 'i(vsense')
            measured = np.abs(c['v(med_y)'].astype(float)) + np.abs(c['v(med_d)'].astype(float))
            t = {'arquivo': name, **cases[i], 'pico_tensoes_diretas_uA': float(voltage_sum.max()) * 1e6,
                 'pico_sondas_uA': float(sense_sum.max()) * 1e6, 'pico_medidor_shunt_uA': float(measured.max()) * 1e6,
                 'diferenca_max_tensoes_sondas_uA': float(np.max(np.abs(voltage_sum - sense_sum))) * 1e6,
                 'diferenca_max_tensoes_medidor_uA': float(np.max(np.abs(voltage_sum - measured))) * 1e6,
                 'corretas': sum(correct_windows(m, i + 1)[1]),
                 'tensoes_fora_tolerancia': int(voltage_sum.max() > 100.005e-6)}
            if name == 'AUDIT_atraso':
                source = current_sum(c, 'i(bcorrecao_')
                resistor = current_sum(c, 'i(rmed')
                t.update(pico_fontes_uA=float(source.max()) * 1e6, pico_resistores_uA=float(resistor.max()) * 1e6,
                         diferenca_max_tensoes_resistores_uA=float(np.max(np.abs(voltage_sum - resistor))) * 1e6)
            rows.append(t)
    (ROOT / 'auditoria_corrente.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(json.dumps(rows, indent=2))

if __name__ == '__main__':
    main()
