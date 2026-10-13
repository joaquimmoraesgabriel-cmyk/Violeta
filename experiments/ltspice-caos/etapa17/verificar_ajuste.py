from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parent
rng=np.random.default_rng(17022026)
y=rng.uniform(0,500,10000)
d=rng.uniform(0,500,10000)
c=90.0
ay=np.where(y+d<=c,y,np.clip((c+y-d)/2,0,c))
ad=np.where(y+d<=c,d,c-ay)
loss=(y-ay)**2+(d-ad)**2
# Busca independente em malha de concessoes; usa toda a cota somente sob escassez.
grid=np.linspace(0,c,1001)
best=((y[:,None]-grid)**2+(d[:,None]-(c-grid))**2).min(axis=1)
assert np.all(loss[y+d>c]<=best[y+d>c]+1e-8)
assert np.all(ay+ad<=c+1e-12)
assert np.allclose(loss[y+d<=c],0)
model=(ROOT/'MLC_coordenador_E_l2.inc').read_text(encoding='utf-8')
for line in model.splitlines():assert line.count('(')==line.count(')'),line
line=next(l for l in model.splitlines() if l.startswith('BfracL2 '))
assert all(x not in line for x in ['falha_','janela(','referencia','entrada_'])
out=dict(aprovado=True,amostras=10000,concessoes_por_malha=1001,
    escopo='Projecao instantanea ANTES do filtro e da prioridade E; nao e otimizacao da resposta logica.')
(ROOT/'verificacao_ajuste.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('Projecao: 10000 pares conferidos contra malha independente de 1001 concessoes.')
