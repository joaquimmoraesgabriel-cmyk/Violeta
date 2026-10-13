from pathlib import Path
import csv,hashlib,json,re
ROOT=Path(__file__).resolve().parent
ts=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
new=[t for t in ts if t['origem']=='etapa17']
jobs=list(dict.fromkeys(n for p in ROOT.glob('lotes_*.json') for n in json.loads(p.read_text(encoding='utf-8'))))
count=sum(len(json.loads((ROOT/f'{n}.json').read_text(encoding='utf-8'))) for n in jobs)
assert count==64 and len(new)==count
assert len(ts)==86
rows=list(csv.DictReader((ROOT/'janelas.csv').open(encoding='utf-8-sig')))
assert len(rows)==len(ts)*17
assert all((r['acerto'] in ['1','True'])==(float(r['margem'])>0) for r in rows)
assert sum(r['acerto'] in ['1','True'] for r in rows)==sum(t['corretas'] for t in ts)
assert sum(t['corretas'] for t in ts if t['arquivo'].startswith('BUF_p3_f'))==198
assert all(not t[k] for t in new for k in ['corrente_falha','corrente_falha_resistores','corrente_falha_sondas','e_sem_saturacao','e_contrario_d'])
assert all(t['pico_comando_e_uA']<=5.000001 and t['pico_concessao_uA']<=90.00002 for t in new)
assert all(t['validador_durante'] for t in new if t['falha_super'] in [1,3])
assert all(not t['validador_durante'] for t in new if t['falha_super'] in [2,4])
assert all(not t['validador_antes'] for t in new)
# Detector de atuacao: falhas do supervisor podem ser invisiveis; nao afirmar deteccao completa.
top=[t for t in new if t['falha_coord']]
assert all(t['latencia_alarme_us'] is not None and t['reserva_retida'] for t in top)
records=[]
for name in jobs:
    files={}
    for ext in ['.cir','.json','.log']:
        p=ROOT/(name+ext);files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    log=(ROOT/f'{name}.log').read_text(encoding='utf-8',errors='replace')
    assert 'Measurement: pico_orcamento' in log
    assert not re.search(r'tolerance relaxed|time step too small|singular matrix',log,re.I)
    records.append(dict(arquivo=name,sha256=files,raw_bytes=(ROOT/f'{name}.raw').stat().st_size))
for name in ['MLC_coordenador_E.inc','MLC_coordenador_E_l2.inc','atuadores_etapa14.inc','UniversalOpAmp2.lib','limitador_tres.inc']:
    records.append(dict(arquivo=name,sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()))
out=dict(aprovado=True,trajetorias_novas=len(new),trajetorias_anteriores=len(ts)-len(new),janelas=len(ts)*17,
    falhas_topo_detectadas=len(top),falsos_alarmes_atuacao=sum(t['alarme_indevido'] for t in new),
    pico_fisico_uA=max(t['pico_tensoes_uA'] for t in new),
    registros=records)
(ROOT/'verificacao_entrega.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='registros'}))
