"""Retencao auditavel e limpeza autorizada dos resultados ate a Etapa 18.

--prepare exporta, valida e registra um plano; --execute aplica esse plano
em outro processo, apos fechamento dos memmaps. Nao altera modelos/resultados.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
WORKSPACE = RESEARCH.parent.parent
EXPECTED = Path('C:/Users/joaqu/Violeta').resolve()
MANIFEST = HERE / 'manifesto_retencao.json'
REPORT = HERE / 'limpeza_executada.json'
REPARSE = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)
OLD = [
    'tests', 'tools', 'reports', 'vscode-seguranca', 'CMakeLists.txt',
    'AMBIENTE_DESENVOLVIMENTO.md', 'LINGUAGEM_T.md', 'QUESTOES_CAPITULO_3.md',
    'REGISTRO_INICIAL_PESQUISA.md', 'RESULTADOS_TESTES_3_4.md',
    'experiments/trit.hpp', 'experiments/README.md',
]
REGENERABLE = ['build', 'LTspice64.msi']


def stamp():
    return datetime.now(timezone.utc).isoformat()


def checked(path: Path, *, exists=True):
    path = path.absolute()
    if WORKSPACE.resolve() != EXPECTED:
        raise ValueError('Workspace inesperado')
    root_info = WORKSPACE.lstat()
    if stat.S_ISLNK(root_info.st_mode) or getattr(root_info, 'st_file_attributes', 0) & REPARSE:
        raise ValueError('Workspace nao pode ser junction/link')
    if path == WORKSPACE or not path.is_relative_to(WORKSPACE):
        raise ValueError(f'Caminho fora do alvo: {path}')
    cursor = path
    while cursor != WORKSPACE:
        if cursor.exists() or cursor.is_symlink():
            info = cursor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & REPARSE:
                raise ValueError(f'Link/junction nao permitido: {cursor}')
        elif exists and cursor == path:
            raise FileNotFoundError(path)
        cursor = cursor.parent
    if path.resolve() != path:
        raise ValueError(f'Resolucao inesperada: {path}')
    return path


def descendants(path):
    checked(path)
    if path.is_file():
        return [path]
    found = []
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            checked(Path(base) / name)
        found.extend(Path(base) / name for name in files)
    return sorted(found)


def digest(path):
    with path.open('rb') as stream:
        value = hashlib.file_digest(stream, 'sha256').hexdigest()
    return value


def metadata(path, hash_file=False):
    info = checked(path).stat()
    result = dict(path=path.relative_to(WORKSPACE).as_posix(), bytes=info.st_size,
                  mtime_ns=info.st_mtime_ns)
    if hash_file:
        result['sha256'] = digest(path)
    return result


def read_text(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8', errors='replace')


def dump(path, data):
    checked(path, exists=False)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def export_stage18():
    sys.path.insert(0, str(RESEARCH / 'etapa12'))
    from leitura_independente import raw_steps

    stage = RESEARCH / 'etapa18'
    output = HERE / 'extratos_etapa18'
    checked(output, exists=False).mkdir(exist_ok=True)
    all_names = list(dict.fromkeys(name for path in sorted(stage.glob('lotes_*.json'))
                                 for name in json.loads(path.read_text(encoding='utf-8'))))
    records = []
    count = 0
    for name in all_names:
        path = stage / f'{name}.raw'
        before = metadata(path)
        cases = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        for index, (time, columns) in enumerate(raw_steps(path, len(cases), max_last_gaps=[c['passo'] for c in cases])):
            count += 1
            names = sorted(columns)
            # Indices reais, sem interpolacao: ate 6000 pontos de visualizacao.
            selected = np.unique(np.linspace(0, len(time)-1, min(6000, len(time)), dtype=np.int64))
            event = np.zeros(len(time), dtype=bool)
            intervals = [(0, .0002), (.0019, .0027)]
            if cases[index]['falha_super'] not in (0, 2, 5) or cases[index]['falha_coord']:
                intervals.extend([(.34320, .34365), (.40320, .40365)])
            tripped = np.flatnonzero(columns['v(trip_cota)'] > .5)
            if len(tripped):
                first = float(time[tripped[0]])
                intervals.append((max(0., first-.0001), min(.85, first+.0001)))
            physical = sum(np.abs((columns[f'v(x{ch}:entrada_shunt)'].astype(float)
                                   - columns[f'v(br_{ch})'].astype(float))/1000) for ch in ('y','d','e'))
            probes = sum(np.abs(columns[f'i(vsense{ch})'].astype(float)) for ch in ('y','d','e'))
            resistors = sum(np.abs(columns[f'i(x{ch}:rshunt)'].astype(float)) for ch in ('y','d','e'))
            peak_indices = [int(np.argmax(v)) for v in (physical, probes, resistors, np.abs(probes-physical))]
            for peak in peak_indices:
                intervals.append((max(0., float(time[peak])-5e-6), min(.85, float(time[peak])+5e-6)))
                event[max(0,peak-8):min(len(time),peak+9)] = True
            for start, end in intervals:
                event |= (time >= start) & (time <= end)
            native = np.flatnonzero(event)
            series = np.column_stack([columns[key][selected] for key in names])
            events = np.column_stack([columns[key][native] for key in names])
            meta = dict(source=before, case_index=index, parameters=cases[index],
                        original_samples=len(time), series_samples=len(selected), native_samples=len(native),
                        native_intervals_s=intervals, peak_indices=peak_indices,
                        purpose='Extrato de visualizacao/replay. Metricas originais em janelas.csv/trajetorias.json; decimacao nao preserva todos os extremos.')
            target = output / f'{name}_caso{index}.npz'
            checked(target, exists=False)
            np.savez_compressed(target, time=time[selected].copy(), values=series,
                                original_indices=selected, native_time=time[native].copy(),
                                native_values=events, native_indices=native,
                                channels=np.array(names), metadata=np.array(json.dumps(meta)))
            with np.load(target, allow_pickle=False) as saved:
                for key in ('time','values','native_time','native_values'):
                    if not np.isfinite(saved[key]).all():
                        raise ValueError(f'Valor nao finito: {target} {key}')
                if len(saved['time']) != len(selected) or saved['values'].shape != (len(selected),len(names)):
                    raise ValueError(f'Dimensoes invalidas: {target}')
                if np.any(np.diff(saved['time']) < 0) or np.any(np.diff(saved['native_time']) < 0):
                    raise ValueError(f'Tempo nao monotono: {target}')
                if saved['time'][0] != time[0] or saved['time'][-1] != time[-1]:
                    raise ValueError(f'Extremos temporais perdidos: {target}')
                if not np.array_equal(saved['values'], series) or not np.array_equal(saved['native_values'], events):
                    raise ValueError(f'Exportacao alterada: {target}')
                if saved['time'][-1] < .85-cases[index]['passo']-1e-12:
                    raise ValueError(f'Trajetoria incompleta: {target}')
            records.append(dict(**metadata(target, True), source=before['path'], case_index=index,
                                original_samples=len(time), series_samples=len(selected), native_samples=len(native),
                                first_time=float(time[0]), last_time=float(time[-1]), channels=len(names)))
        if metadata(path) != before:
            raise ValueError(f'RAW alterado durante exportacao: {path}')
        print(f'Exportado {name}: {len(cases)} casos validados', flush=True)
    if count != 64:
        raise ValueError(f'Total de trajetorias inesperado: {count}')
    dump(HERE/'indice_extratos.json', dict(created_utc=stamp(), cases=count, sources=len(all_names), files=records))
    return records


def archive_old():
    paths = [WORKSPACE / item for item in OLD if (WORKSPACE / item).exists()]
    files = [file for path in paths for file in descendants(path)]
    archive = HERE / 'pesquisas_anteriores_fontes.zip'
    checked(archive, exists=False)
    file_records = [metadata(path, True) for path in files]
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in files:
            zipped.write(path, path.relative_to(WORKSPACE).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise ValueError('ZIP corrompido')
        for record in file_records:
            if hashlib.sha256(zipped.read(record['path'])).hexdigest() != record['sha256']:
                raise ValueError(f'Arquivo nao preservado no ZIP: {record["path"]}')
    return metadata(archive, True), file_records


def prepare():
    if MANIFEST.exists() or REPORT.exists():
        raise ValueError('Plano existente: nao sobrescrever evidencias')
    free_before = shutil.disk_usage(WORKSPACE).free
    exports = export_stage18()
    archive, old_files = archive_old()
    removal, retained = [], []
    for path in sorted(RESEARCH.rglob('*.raw')):
        if path.name.endswith('.log.raw'):
            continue
        rel = path.relative_to(RESEARCH)
        match = re.match(r'etapa(\d+)$', rel.parts[0]) if len(rel.parts)>1 else None
        if len(rel.parts)>1 and (not match or int(match[1])>18):
            continue
        log = path.with_suffix('.log')
        text = read_text(log) if log.exists() else ''
        reason = ('smoke preservado' if 'smoke' in path.stem.lower() else
                  'sem marcador de conclusao' if 'Total elapsed time' not in text else
                  'sem medidas leves no log' if 'Measurement:' not in text else None)
        record = metadata(path)
        record['evidence'] = [metadata(p, True) for p in (path.with_suffix('.cir'),log,path.with_suffix('.json')) if p.exists()]
        if reason:
            retained.append(dict(**record, reason=reason))
        else:
            removal.append(record)
    non_research = []
    for item in OLD + REGENERABLE:
        path = WORKSPACE / item
        if path.exists():
            files = descendants(path)
            non_research.append(dict(path=item, is_directory=path.is_dir(),
                                     files=[metadata(p) for p in files], bytes=sum(p.stat().st_size for p in files),
                                     archived=item in OLD))
    plan = dict(created_utc=stamp(), workspace=str(WORKSPACE), free_before_bytes=free_before,
                exports=exports, archive=archive, archived_files=old_files,
                remove_raw=removal, preserve_raw=retained, remove_non_research=non_research,
                expected_freed_bytes=sum(r['bytes'] for r in removal+non_research),
                policy='Resultados leves/fontes/modelos/logs preservados. RAWs sem conclusao ou sem medidas permanecem. ZIP validado para fontes de pesquisas anteriores.')
    dump(MANIFEST, plan)
    print(json.dumps(dict(prepared=True, remove_raw=len(removal), preserve_raw=len(retained),
                          exports=len(exports), expected_freed_gib=plan['expected_freed_bytes']/2**30,
                          export_gib=sum(e['bytes'] for e in exports)/2**30), indent=2), flush=True)


def unchanged(record):
    path = checked(WORKSPACE / record['path'])
    info = path.stat()
    if info.st_size != record['bytes'] or info.st_mtime_ns != record['mtime_ns']:
        raise ValueError(f'Arquivo mudou desde planejamento: {path}')
    if 'sha256' in record and digest(path) != record['sha256']:
        raise ValueError(f'Hash mudou: {path}')
    return path


def execute():
    if REPORT.exists():
        raise ValueError('Limpeza ja executada; evidencias preservadas')
    plan = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if plan['workspace'] != str(WORKSPACE):
        raise ValueError('Manifesto de outro workspace')
    # Validar tudo antes da primeira remocao.
    unchanged(plan['archive'])
    for record in plan['exports']:
        unchanged(record)
    for record in plan['remove_raw']:
        unchanged(record)
        for evidence in record['evidence']:
            unchanged(evidence)
    for entry in plan['remove_non_research']:
        path = checked(WORKSPACE/entry['path'])
        actual = {p.relative_to(WORKSPACE).as_posix() for p in descendants(path)}
        if actual != {r['path'] for r in entry['files']}:
            raise ValueError(f'Conteudo de pasta mudou: {path}')
        for record in entry['files']:
            unchanged(record)
    deleted=[]
    for record in plan['remove_raw']:
        checked(WORKSPACE/record['path']).unlink()
        deleted.append(record['path'])
    for entry in plan['remove_non_research']:
        path=checked(WORKSPACE/entry['path'])
        # No recursive shell, and all descendants were checked for reparse points.
        if entry['is_directory']:
            shutil.rmtree(path)
        else:
            path.unlink()
        deleted.append(entry['path'])
    if any((WORKSPACE/record['path']).exists() for record in plan['remove_raw']):
        raise ValueError('RAW remanescente inesperado')
    if any(not (WORKSPACE/r['path']).exists() for r in plan['preserve_raw']):
        raise ValueError('Retencao inesperadamente ausente')
    free_after=shutil.disk_usage(WORKSPACE).free
    report=dict(completed_utc=stamp(), removed_raw=len(plan['remove_raw']),
                retained_raw=len(plan['preserve_raw']), exported_cases=len(plan['exports']),
                bytes_removed=plan['expected_freed_bytes'], free_before_bytes=plan['free_before_bytes'],
                free_after_bytes=free_after, observed_free_delta_bytes=free_after-plan['free_before_bytes'],
                exports_bytes=sum(e['bytes'] for e in plan['exports']), archive=plan['archive'], deleted=deleted)
    dump(REPORT,report)
    note=f'''RETENCAO E LIMPEZA AUTORIZADA — {report['completed_utc']}

Foram removidos {report['removed_raw']} RAWs principais de simulacoes concluidas ate a Etapa18.
Espaco dos arquivos removidos: {report['bytes_removed']/2**30:.3f} GiB.
Espaco livre observado depois: {free_after/2**30:.3f} GiB.
Foram preservados modelos, netlists, bibliotecas, parametros, logs, CSVs, JSONs, relatorios e scripts da pesquisa.
Os {report['retained_raw']} RAWs retidos estao enumerados no manifesto (SMOKE, preliminares incompletos ou ausencia de medidas leves).

As 64 trajetorias da Etapa18 foram exportadas para NPZ comprimidos, com todas as colunas salvas no RAW,
ate6000 amostras nativas por curva e trechos de eventos/picos em resolucao original. Exportacao reaberta e
validada quanto a finitude, igualdade com a selecao original, quantidade de casos e cobertura temporal.
O indice_extratos.json descreve dimensoes, fontes e hashes dos extratos.
Os NPZ sao arquivos de visualizacao/replay: a decimacao nao conserva todos os extremos ou a forma de onda inteira.
As metricas de publicacao permanecem nos resultados originais, sem recalculo a partir de pontos reduzidos.

Referencias anteriores a RAWs preservados descrevem o estado da entrega original. A partir desta manutencao,
os RAWs enumerados em manifesto_retencao.json foram substituidos por metricas leves e extratos selecionados.
Reanalises que dependam das amostras removidas exigem repetir a simulacao. O manifesto guarda tamanho/mtime
dos RAWs e SHA256 de netlist/log/parametros quando presentes; nao afirma ter hash integral dos RAWs.

Fontes e textos de pesquisas anteriores (ternarios e seguranca) foram arquivados no ZIP validado
pesquisas_anteriores_fontes.zip antes da retirada das pastas ativas. Build e instalador eram regeneraveis.
.git e LICENSE foram mantidos. Nenhum processo LTspice foi encerrado.
'''
    (HERE/'NOTA_RETENCAO.txt').write_text(note,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('deleted','archive')},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true')
    group.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        prepare()
    else:
        execute()
