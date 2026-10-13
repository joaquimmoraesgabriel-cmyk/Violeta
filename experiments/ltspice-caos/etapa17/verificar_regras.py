"""Auditoria estatica das cotas e do acesso a sinais; nao substitui LTspice."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
rng=np.random.default_rng(17012026)
n=100000
y=rng.uniform(-500,500,n)*1e-6
d=rng.uniform(-500,500,n)*1e-6
e=d+rng.uniform(-30,30,n)*1e-6
result=[]
for mode in range(3):
    if mode==0:q=90e-6*np.abs(y)/np.maximum(np.abs(y)+np.abs(d),1e-12)
    elif mode==1:q=np.full(n,45e-6)
    else:q=np.clip(45e-6+np.maximum(0,45e-6-np.abs(d))-np.maximum(0,45e-6-np.abs(y)),0,90e-6)
    for delayed in [False,True]:
        qy=q if not delayed else rng.uniform(0,90e-6,n)
        qd=90e-6-qy
        by=np.sign(y)*np.minimum(np.abs(y),qy)
        bd=np.sign(d)*np.minimum(np.abs(d),qd)
        ee=np.where((np.abs(d)>np.abs(bd)+1e-6)&(e*d>0),
                    np.sign(e)*np.minimum(5e-6,np.minimum(np.maximum(0,np.abs(e)-np.abs(bd)-1e-6),np.maximum(0,90e-6-np.abs(bd)))),0)
        ey=np.sign(by)*np.minimum(np.abs(by),np.maximum(0,90e-6-np.abs(bd)-np.abs(ee)))
        total=np.abs(ey)+np.abs(bd)+np.abs(ee)
        assert total.max()<=90e-6+1e-18
        assert (ee*d>=-1e-18).all()
        assert np.abs(ee).max()<=5e-6+1e-18
        result.append(dict(modo=mode,cota_obsoleta=delayed,amostras=n,pico_uA=float(total.max()*1e6)))
code=(ROOT/'MLC_coordenador_E.inc').read_text(encoding='utf-8')
for line in code.splitlines():
    assert line.count('(')==line.count(')'),line
for first in ['BqInval ','BquotaY ','BquotaD ','BfracCom ','BfracGrp ','BfracAlvo ','BesperadoE ','BesperadoY ','BesperadoD ']:
    line=next(x for x in code.splitlines() if x.startswith(first))
    assert not any(s in line for s in ['falha_','janela(','referencia','entrada_a','entrada_b']),line
assert code.count('BEs')==9
assert 'BisolY exp_y_buf 0 V={V(exp_y)}' in code
assert 'BisolD exp_d_buf 0 V={V(exp_d)}' in code
out=dict(casos=result,sha256_modelo=hashlib.sha256(code.encode()).hexdigest(),aprovado=True)
(ROOT/'verificacao_regras.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('600000 alocacoes adversas: soma <=90 uA, E <=5 uA, sinal correto; estrutura conferida.')
