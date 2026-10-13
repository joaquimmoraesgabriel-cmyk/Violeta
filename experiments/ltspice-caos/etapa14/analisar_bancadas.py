"""Conferencia externa das bancadas; transientes rejeitados sao preservados."""
from pathlib import Path
import json
import re
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa12'))
from leitura_independente import raw_steps

def analyze():
    rows = []
    for name in ['BANCADA_limite', 'BANCADA_limite_ref', 'BANCADA_intertravado', 'BANCADA_intertravado_ref',
                 'BANCADA_antiwindup', 'BANCADA_antiwindup_ref', 'BANCADA_filtrado', 'BANCADA_filtrado_ref', 'BANCADA_tolerancias']:
        meta = 'BANCADA_tolerancias.json' if 'tolerancias' in name else ('BANCADA_filtrado.json' if 'filtrado' in name else 'BANCADA_limite.json')
        cases = json.loads((ROOT / meta).read_text())
        data = (ROOT / f'{name}.log').read_bytes()
        text = data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8', errors='replace')
        if len(re.findall(r'^\.step ', text, re.M)) != len(cases):
            raise ValueError(f'{name}: passos incompletos')
        measures = {n: {int(i): float(v) for i, v in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)', body, re.M)}
                    for n, body in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)', text, re.S)}
        if any(len(measures.get(k, {})) != len(cases) for k in ['pico', 'patamar']):
            raise ValueError(f'{name}: medidas incompletas')
        for i, (time, c) in enumerate(raw_steps(ROOT / f'{name}.raw', len(cases), .0004)):
            actual = np.abs(c['i(vloady)'].astype(float)) + np.abs(c['i(vloadx)'].astype(float))
            peak = int(np.argmax(actual))
            rows.append({'arquivo': name, **cases[i], 'pico_correntes_uA': float(actual[peak]) * 1e6,
                         'tempo_pico_us': float(time[peak]) * 1e6, 'pico_monitor_uA': measures['pico'][i + 1] * 1e6,
                         'patamar_uA': measures['patamar'][i + 1] * 1e6,
                         'fora_tolerancia': int(actual[peak] > 100.005e-6),
                         'tempo_acima_teto_us': float(np.trapezoid((actual > 100.005e-6).astype(float), time)) * 1e6})
    (ROOT / 'bancadas_resultados.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    selected = [r for r in rows if r['arquivo'].startswith('BANCADA_filtrado') and r['margem_limite'] == 90e-6 and r['gbw_limit'] == 100e6 and r['tau_cmd'] == 2e-6]
    if len(selected) != 2 or any(r['fora_tolerancia'] for r in selected):
        raise ValueError('Candidato escolhido nao passou em ambos os ensaios da bancada')
    tolerances = [r for r in rows if r['arquivo'] == 'BANCADA_tolerancias']
    if len(tolerances) != 8 or any(r['fora_tolerancia'] for r in tolerances):
        raise ValueError('Candidato falhou na verificacao de tolerancias da bancada')
    (ROOT / 'candidato_limitador.json').write_text(json.dumps({'margem_limite': 90e-6, 'gbw_limit': 100e6, 'tau_cmd': 2e-6,
                                                             'pico_verificado_uA': max(r['pico_correntes_uA'] for r in selected),
                                                             'ensaios': selected}, indent=2), encoding='utf-8')
    print(json.dumps({'trajetorias_bancada': len(rows), 'candidato_pico_uA': max(r['pico_correntes_uA'] for r in selected),
                      'falhas_preservadas': sum(r['fora_tolerancia'] for r in rows)}, indent=2))

if __name__ == '__main__':
    analyze()
