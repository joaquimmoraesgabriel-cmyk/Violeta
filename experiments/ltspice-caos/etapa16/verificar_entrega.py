"""Verifica cobertura, leitura final e separacao entre falhas logicas e integridade da evidencia."""
from pathlib import Path
import csv,hashlib,json,re
ROOT=Path(__file__).resolve().parent
ts=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
with (ROOT/'janelas.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
jobs=[]
for p in ROOT.glob('lotes_*.json'):jobs+=json.loads(p.read_text(encoding='utf-8'))
assert len(jobs)==len(set(jobs))
expected=sum(len(json.loads((ROOT/f'{n}.json').read_text(encoding='utf-8'))) for n in jobs)
new=[t for t in ts if t['origem']=='etapa16']
assert len(new)==expected==82
assert len(ts)==98 and len(rows)==1666
assert {t['arquivo'] for t in new}==set(jobs)
for t in ts:
    rr=[r for r in rows if r['arquivo']==t['arquivo'] and int(r['caso'])==t['caso']]
    assert len(rr)==17
    assert sum(int(r['acerto']) for r in rr)==t['corretas']
    assert sorted(int(r['janela']) for r in rr)==list(range(17))
    assert not t['corrente_falha'] and not t['corrente_falha_resistores'] and not t['corrente_falha_sondas']
    if 'e_sem_saturacao' in t:
        assert not t['e_sem_saturacao'] and not t['e_contrario_d']
        assert t['pico_comando_e_uA']<=t['cap_e']*1e6+.0001
refs=[t for t in ts if t['origem']=='etapa15']
assert sum(t['corretas'] for t in refs)==198
for path in ROOT.glob('MLC*.inc'):
    text=path.read_text(encoding='utf-8')
    assert 'BisolY exp_y_buf' in text and 'BisolD exp_d_buf' in text
    if path.name!='MLC_referencia.inc':
        assert len(re.findall(r'^BEs\d ',text,re.M))==9
        assert 'BesperadoE' in text
        eline=next(l for l in text.splitlines() if l.startswith('BesperadoE'))
        assert 'falha_coord' not in eline and 'janela(' not in eline
        assert 'referencia' not in eline
        if '_v2' in path.name:assert 'cap_operacao-abs(V(base_d))' in eline
manifest={}
for name in jobs:
    manifest[name]={}
    for ext in ['.cir','.json','.log']:
        p=ROOT/(name+ext)
        manifest[name][ext]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    manifest[name]['.raw']=dict(bytes=(ROOT/(name+'.raw')).stat().st_size)
out=dict(integridade_aprovada=True,trajetorias_novas=len(new),trajetorias_historicas=len(refs),janelas=len(rows),
         janelas_logicas_falhas=sum(17-t['corretas'] for t in ts),
         alarmes_indevidos_novos=sum(t['alarme_indevido'] for t in new),
         pico_corrente_uA=max(t['pico_tensoes_uA'] for t in new),
         alcance='Integridade e criterio de corrente aprovados; nao equivale a aprovar todas as janelas logicas.',
         arquivos=manifest)
(ROOT/'verificacao_entrega.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='arquivos'},indent=2))
