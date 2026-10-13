"""Leitura de RAW real e .meas completos, com verificacao de passos e duracao."""
from pathlib import Path
import re
import numpy as np

def measurements(path, count):
    data = Path(path).read_bytes()
    text = data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8', errors='replace')
    steps = re.findall(r'^\.step (.+)$', text, re.M)
    if len(steps) != count:
        raise ValueError(f'{path}: {len(steps)} passos, esperados {count}')
    found = {name: {int(i): float(value) for i, value in re.findall(r'^\s*(\d+)\s+([-+\d.eE]+)', body, re.M)}
             for name, body in re.findall(r'Measurement: (\w+)\s*\n(.*?)(?=\nMeasurement:|\Z)', text, re.S)}
    required = [f'{name}_{i:02}' for i in range(17) for name in ['minimo', 'maximo']] + ['pico_orcamento']
    for key in required:
        if set(found.get(key, {})) != set(range(1, count + 1)):
            raise ValueError(f'{path}: medida incompleta {key}')
    return found

def raw_steps(path, expected, end_time=.85, max_last_gaps=None):
    path = Path(path)
    with path.open('rb') as stream:
        prefix = stream.read(32768)
    marker = 'Binary:\n'.encode('utf-16-le')
    pos = prefix.find(marker)
    if pos < 0:
        marker = 'Binary:\r\n'.encode('utf-16-le')
        pos = prefix.find(marker)
    if pos < 0:
        raise ValueError(f'{path}: cabecalho RAW nao reconhecido')
    header = prefix[:pos].decode('utf-16-le')
    names = re.findall(r'^\s*\d+\s+(\S+)\s+\S+', header, re.M)
    if not names or names[0].lower() != 'time' or 'Flags: real' not in header:
        raise ValueError(f'{path}: formato RAW inesperado')
    offset = pos + len(marker)
    dtype = np.dtype([('time', '<f8'), ('v', '<f4', (len(names) - 1,))])
    size = path.stat().st_size - offset
    if size % dtype.itemsize:
        raise ValueError(f'{path}: RAW truncado')
    rec = np.memmap(path, mode='r', offset=offset, dtype=dtype, shape=(size // dtype.itemsize,))
    cuts = np.r_[0, np.flatnonzero(np.diff(rec['time']) < 0) + 1, len(rec)]
    if len(cuts) - 1 != expected:
        raise ValueError(f'{path}: quantidade inesperada de trajetorias')
    if max_last_gaps is not None:
        if len(max_last_gaps)!=expected or any(g<=0 for g in max_last_gaps):
            raise ValueError('Limites de lacuna final invalidos')
    for index,(a, b) in enumerate(zip(cuts[:-1], cuts[1:])):
        values = rec[a:b]
        # LTspice pode encerrar um step sem gravar exatamente tstop: conferir
        # com o passo maximo explicitamente informado, sem interpolar dados.
        gap=max_last_gaps[index]+1e-12 if max_last_gaps is not None else min(1e-6,end_time*1e-6)
        if values[-1]['time'] < end_time - gap:
            raise ValueError(f'{path}: transitorio incompleto')
        columns = {name.lower(): values['v'][:, i] for i, name in enumerate(names[1:])}
        yield values['time'], columns

def current_sum(columns, prefix):
    arrays = [v.astype(np.float64) for key, v in columns.items() if key.startswith(prefix.lower())]
    if not arrays:
        raise ValueError(f'Nenhuma corrente com prefixo {prefix}')
    return sum(np.abs(v) for v in arrays)

def correct_windows(measures, step):
    seq = [0, 0, 1, 0, 2, 0, 3, 1, 1, 2, 1, 3, 2, 2, 3, 3, 0]
    margins = [measures[f'minimo_{i:02}'][step] if code == 3 else -measures[f'maximo_{i:02}'][step] for i, code in enumerate(seq)]
    return margins, [int(margin > 0) for margin in margins]
