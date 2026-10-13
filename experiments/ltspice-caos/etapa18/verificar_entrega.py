"""Validacao da entrega completa; alarmes indevidos sao achados, nao omitidos."""
from pathlib import Path
import csv,hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
T=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
R=list(csv.DictReader((ROOT/'janelas.csv').open(encoding='utf-8-sig')))
planned=list(dict.fromkeys(n for p in ROOT.glob('lotes_*.json') for n in json.loads(p.read_text(encoding='utf-8'))))
assert len(T)==64 and len(R)==1088
assert {t['arquivo'] for t in T}==set(planned)
assert not json.loads((ROOT/'pendentes.json').read_text(encoding='utf-8'))
assert len({(t['arquivo'],t['caso']) for t in T})==64
assert sum(t['corretas'] for t in T)==sum(r['acerto'] in ['1','True'] for r in R)
assert all(not t[k] for t in T for k in ['corrente_falha','corrente_falha_resistores','corrente_falha_sondas','cota_limite_falha','e_sem_saturacao','e_contrario_d'])
assert all(t['pico_comando_e_uA']<=5.00001 for t in T)
assert all(t['cota_erro_reserva_local_uA'] is None or t['cota_erro_reserva_local_uA']<.00005 for t in T)
for t in T:
    if t['cota_alarme_detectado']:
        assert not t['cota_alarme_indevido'] and t['cota_alarme_durante']
        deadline=850000 if t['falha_super'] in [2,5] else 60000
        assert 0<=t['cota_latencia_alarme_us']<=deadline
    else:
        assert t['cota_latencia_alarme_us'] is None
pre=json.loads((ROOT/'verificacao_modelo.json').read_text(encoding='utf-8'))
assert pre['sha256_modelo']==hashlib.sha256((ROOT/'MLC_cotas_v1.inc').read_bytes()).hexdigest()
assert pre['sha256_v2']==hashlib.sha256((ROOT/'MLC_cotas_v2.inc').read_bytes()).hexdigest()
raw_checked=0;max_margin_difference=0
provenance=[]
codes=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
for name in planned:
    cases=[t for t in T if t['arquivo']==name]
    assert [p['caso'] for p in cases]==list(range(len(cases)))
    deck=(ROOT/f'{name}.cir').read_text(encoding='utf-8')
    params=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
    tables=dict(re.findall(r'^\.param (\w+)=table\(caso,([^\n]+)\)$',deck,re.M))
    for key in params[0]:
        if key in ['caso','nome_perfil']:continue
        values=[float(v) for v in tables[key].split(',')]
        assert values[::2]==list(range(len(params))),(name,key,'indices')
        assert values[1::2]==[p[key] for p in params],(name,key,'valores')
        assert values[1::2]==[p[key] for p in cases],(name,key,'analise')
    blob=(ROOT/f'{name}.log').read_bytes()
    log=blob.decode('utf-16' if blob.startswith(b'\xff\xfe') else 'utf-8')
    assert [int(v) for v in re.findall(r'^\.step caso=(\d+)\s*$',log,re.M)]==list(range(len(cases))),name
    target={(int(r['caso']),int(r['janela'])):r for r in R if r['arquivo']==name}
    for case,(t,c) in enumerate(raw_steps(ROOT/f'{name}.raw',len(cases),max_last_gaps=[p['passo'] for p in cases])):
        x=c['v(x)']
        for j,code in enumerate(codes):
            lo=j*.05+.03;hi=j*.05+.049
            a,b=np.searchsorted(t,[lo,hi],side='left');boundary=np.interp([lo,hi],t,x)
            raw_margin=min(float(x[a:b].min()),float(boundary.min())) if code==3 else -max(float(x[a:b].max()),float(boundary.max()))
            row=target[case,j];delta=abs(raw_margin-float(row['margem']));max_margin_difference=max(max_margin_difference,delta)
            assert (raw_margin>0)==(row['acerto'] in ['1','True']),(name,case,j,raw_margin,row)
            assert delta<.0002,(name,case,j,delta)
            raw_checked+=1
    files={}
    for ext in ['.cir','.json','.log','.raw']:
        p=ROOT/f'{name}{ext}';st=p.stat()
        files[ext]=dict(bytes=st.st_size,mtime_ns=st.st_mtime_ns)
        if ext!='.raw':files[ext]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    provenance.append(dict(nome=name,arquivos=files))
libraries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.inc')}
libraries['UniversalOpAmp2.lib']=hashlib.sha256((ROOT/'UniversalOpAmp2.lib').read_bytes()).hexdigest()
analysis_sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
    ['analisar_etapa18.py','verificar_entrega.py','verificar_modelo.py',
     '../etapa16/analisar_etapa16.py','../etapa12/leitura_independente.py']}
out=dict(trajetorias=64,janelas=1088,janelas_conferidas_raw=raw_checked,
    maior_diferenca_margem_raw_meas=max_margin_difference,checagens_corrente_aprovadas=64,
    maior_lacuna_final_us=max(t['lacuna_final_us'] for t in T),
    alarmes_cota_indevidos=sum(t['cota_alarme_indevido'] for t in T),
    notas='RAW identificado por tamanho/mtime; demais fontes e logs por SHA256. Alarmes indevidos preservados como falha funcional.',
    bibliotecas=libraries,analise_sha256=analysis_sources,fontes=provenance)
(ROOT/'verificacao_entrega.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ['bibliotecas','analise_sha256','fontes']}))
