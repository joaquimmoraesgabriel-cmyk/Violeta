"""Inventario somente leitura para a retencao dos resultados LTspice."""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def text_file(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8', errors='replace')

def main():
    records = []
    for path in ROOT.rglob('*.raw'):
        if path.name.endswith('.log.raw'):
            continue
        log = path.with_suffix('.log')
        txt = text_file(log) if log.exists() else ''
        records.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                            complete_marker='Total elapsed time' in txt,
                            log_exists=log.exists(), tail=txt[-300:] if 'Total elapsed time' not in txt else None))
    inventory = HERE / ('inventario_atual.json' if (HERE/'inventario_previo.json').exists() else 'inventario_previo.json')
    inventory.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(json.dumps(dict(files=len(records), bytes=sum(r['bytes'] for r in records),
                          complete=sum(r['complete_marker'] for r in records),
                          exceptions=[r for r in records if not r['complete_marker']]), indent=2))
    sample = ROOT/'etapa18/L2_5_10_v2.raw'
    if sample.exists():
        with sample.open('rb') as stream:
            prefix=stream.read(32768)
        pos=prefix.find('Binary:'.encode('utf-16-le'))
        print(prefix[:pos].decode('utf-16-le'))
    else:
        print('RAW de referencia removido conforme manifesto de retencao, se a limpeza ja ocorreu.')

if __name__ == '__main__':
    main()
