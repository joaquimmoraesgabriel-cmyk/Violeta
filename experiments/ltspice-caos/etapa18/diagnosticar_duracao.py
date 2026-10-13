"""Diagnostico parcial de incoerencia saudavel em primeira trajetoria."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
for name in ['C_sadio_on','L2_5_10','L2_1_2','L2_20_50_off','L2_5_10_off']:
    p=ROOT/f'{name}.raw'
    if not p.exists():continue
    with p.open('rb') as f:prefix=f.read(32768)
    marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
    if pos<0:continue
    names=[n.lower() for n in re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)]
    dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);off=pos+len(marker)
    rec=np.memmap(p,mode='r',offset=off,dtype=dtype,shape=((p.stat().st_size-off)//dtype.itemsize,))
    cuts=np.flatnonzero(np.diff(rec['time'])<0);r=rec[:cuts[0]+1] if len(cuts) else rec
    t=r['time'];c={n:r['v'][:,i] for i,n in enumerate(names[1:])}
    m=t>=.03
    if not np.any(m):continue
    e=c['v(erro_cota)'][m].astype(float)*1e6;tt=t[m];hit=e>6.5
    edges=np.flatnonzero(np.diff(np.r_[False,hit,False].astype(int)))
    lengths=[tt[min(b,len(tt)-1)]-tt[a] for a,b in zip(edges[::2],edges[1::2])]
    print(json.dumps(dict(arquivo=name,ate_s=float(t[-1]),maior_erro_uA=float(e.max()),
        fracao_tempo_incoerente=float(np.trapezoid(hit.astype(float),tt)/(tt[-1]-tt[0])),
        maior_trecho_us=max(lengths,default=0)*1e6,primeira_trajetoria_completa=bool(len(cuts)))))
