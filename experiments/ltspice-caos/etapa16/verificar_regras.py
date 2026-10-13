"""Checa a mediana e o orcamento estatico em entradas adversas, independente do LTspice."""
from pathlib import Path
import json
import numpy as np
rng=np.random.default_rng(160012)
a=rng.normal(size=(10000,9));a[:512]=np.array([[(k>>i)&1 for i in range(9)] for k in range(512)])
b=a.copy()
for p in range(9):
    for i in range(p%2,8,2):
        lo=np.minimum(b[:,i],b[:,i+1]);hi=np.maximum(b[:,i],b[:,i+1])
        b[:,i]=lo;b[:,i+1]=hi
assert np.array_equal(b,np.sort(a,axis=1))
y,d,e=rng.uniform(-300e-6,300e-6,size=(3,100000))
initial_failures=[]
for mode in [1,2]:
    gain=np.minimum(1,(90e-6-(20e-6 if mode==1 else 0))/np.maximum(np.abs(y)+np.abs(d),1e-12))
    dd=d*gain
    ee=np.where((np.abs(d)>np.abs(dd)+1e-6)&(d*e>0),np.sign(e)*np.minimum(20e-6,np.maximum(0,np.abs(e)-np.abs(dd)-1e-6)),0)
    yy=y*gain if mode==1 else np.sign(y)*np.minimum(np.abs(y*gain),np.maximum(0,90e-6-np.abs(dd)-np.abs(ee)))
    initial_failures.append(dict(modo=mode,pico_soma_referencias_uA=float((np.abs(yy)+np.abs(dd)+np.abs(ee)).max()*1e6)))
    ee=np.sign(ee)*np.minimum(np.abs(ee),np.maximum(0,90e-6-np.abs(dd)))
    yy=y*gain if mode==1 else np.sign(y)*np.minimum(np.abs(y*gain),np.maximum(0,90e-6-np.abs(dd)-np.abs(ee)))
    assert (np.abs(yy)+np.abs(dd)+np.abs(ee)).max()<=90e-6+1e-18
    assert (ee*d>=0).all()
    assert not np.any((np.abs(ee)>0)&(np.abs(d)<=np.abs(dd)+1e-6))
out=dict(vetores_mediana=10000,binarios_exaustivos=512,alocacoes_por_modo=100000,modos=2,aprovado_v2=True,
         diagnostico_referencias_v1=initial_failures,
         alcance='Regras algebricas; nao valida dinamica, hardware ou convergencia numerica.')
(Path(__file__).resolve().parent/'verificacao_regras.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
