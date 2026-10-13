"""Resume medições reais do LTspice; não gera resultados simulados."""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_log(path):
    text = path.read_bytes().decode('utf-16' if path.read_bytes().startswith(b'\xff\xfe') else 'utf-8', errors='replace')
    steps = re.findall(r'^\.step (.+)$', text, re.M)
    measurements = {}
    for name, block in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)', text, re.S):
        measurements[name] = {int(index): float(value) for index, value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)', block, re.M)}
    if not steps or any(name not in measurements for name in ('tensao', 'resultado', 'esperado', 'erro', 'margem')):
        raise RuntimeError(f'Medições ausentes ou simulação incompleta: {path.name}')
    rows = []
    for index, step in enumerate(steps, 1):
        params = dict((name, float(value)) for name, value in re.findall(r'(\w+)=([-+\d.eE]+)', step))
        case = int(params['caso'])
        row = {
            'arquivo': path.name, 'passo': index, 'caso': case,
            'erro_sensor': params.get('erro_sensor', 0),
            'refinamento': params.get('refinamento', 1),
            'desvio_R_percentual': (case // 8 - 3) * 0.5,
            'controle': (case % 8) // 4,
            'A': (case % 4) // 2, 'B': case % 2,
        }
        for name, values in measurements.items():
            if index not in values:
                raise RuntimeError(f'Medição {name} sem passo {index}: {path.name}')
            row[name] = values[index]
        rows.append(row)
    return rows


def main():
    paths = [ROOT / filename for filename in sys.argv[1:]] if len(sys.argv) > 1 else [ROOT / 'Hipotese_pilar_AND.log']
    rows = [row for path in paths for row in parse_log(path)]
    with (ROOT / 'resultados_hipotese.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for filename, sensor, refinement in sorted(set((row['arquivo'], row['erro_sensor'], row['refinamento']) for row in rows)):
        for control in (0, 1):
            subset = [row for row in rows if row['arquivo'] == filename and row['erro_sensor'] == sensor and row['controle'] == control and row['refinamento'] == refinement]
            if not subset:
                continue
            summary.append({
                'arquivo': filename, 'erro_sensor_percentual': sensor * 100,
                'passo_maximo_ns': 100 / refinement,
                'controle': control, 'casos': len(subset),
                'acertos': sum(row['erro'] == 0 for row in subset),
                'menor_margem_V': min(row['margem'] for row in subset),
                'nominal': [{'A': row['A'], 'B': row['B'], 'tensao': row['tensao'], 'resultado': row['resultado']} for row in subset if row['desvio_R_percentual'] == 0],
            })
    (ROOT / 'resumo_hipotese.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
