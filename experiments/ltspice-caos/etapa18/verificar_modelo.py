"""Propriedades estruturais do controle, sem substituir simulacoes."""
from pathlib import Path
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
model=(ROOT/'MLC_cotas_v1.inc').read_text(encoding='utf-8')
v2=(ROOT/'MLC_cotas_v2.inc').read_text(encoding='utf-8')
assert v2==model.replace('(1-V(timer_cota))/(20u/1n),-V(timer_cota)/(40u/1n)', '(1-V(timer_cota))/(50u/1n),-V(timer_cota)/(20u/1n)')
monitor=model.split('* MONITOR INDEPENDENTE:')[1].split('* FIM MONITOR.')[0]
for forbidden in ['falha_', 'janela(', 'V(pert_', 'V(referencia)', 'V(frac_alvo)', 'V(frac_filtro)']:
    assert forbidden not in monitor,forbidden
names=[]
for line in model.splitlines():
    if not line or line[0] in '.*':continue
    names.append(line.split()[0].lower())
assert len(names)==len(set(names)), 'Componentes duplicados'
rng=np.random.default_rng(18012);n=200000
y=rng.uniform(-300e-6,300e-6,n);d=rng.uniform(-300e-6,300e-6,n);er=d+rng.normal(0,5e-6,n)
C=90e-6
for label,qy in [('normal',rng.uniform(0,C,n)),('local',C*np.abs(y)/np.maximum(np.abs(y)+np.abs(d),1e-12)),('guarda',np.full(n,C/2))]:
    qd=C-qy;by=np.sign(y)*np.minimum(np.abs(y),qy);bd=np.sign(d)*np.minimum(np.abs(d),qd)
    ee=np.where((np.abs(d)>np.abs(bd)+1e-6)&(er*d>0),np.sign(er)*np.minimum(5e-6,np.minimum(np.maximum(0,np.abs(er)-np.abs(bd)-1e-6),np.maximum(0,C-np.abs(bd)))),0)
    ey=np.sign(by)*np.minimum(np.abs(by),np.maximum(0,C-np.abs(bd)-np.abs(ee)))
    assert np.max(np.abs(ey)+np.abs(bd)+np.abs(ee))<=C+1e-18,label
    assert np.max(np.abs(ee))<=5e-6+1e-18,label
manifest={p.name:json.loads(p.read_text(encoding='utf-8')) for p in ROOT.glob('lotes_*.json')}
cases=[c for jobs in manifest.values() for name in jobs for c in json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))]
assert len(cases)==64,len(cases)
result=dict(casos_alocacao=3*n,trajetorias_planejadas=len(cases),sem_acesso_do_monitor_a_falha=True,
            sha256_modelo=hashlib.sha256((ROOT/'MLC_cotas_v1.inc').read_bytes()).hexdigest(),
            sha256_v2=hashlib.sha256((ROOT/'MLC_cotas_v2.inc').read_bytes()).hexdigest(),
            intervalo_idade_cantos_us=[20-10-.85*25,20+10+.85*25],
            nota='Verificacao algebrica e estrutural; nao prova realizacao em hardware.')
(ROOT/'verificacao_modelo.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
