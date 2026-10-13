"""Primeiros alarmes na primeira trajetoria gravada; nao certifica conclusao."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
for p in ROOT.glob('*.raw'):
    if p.stem=='SMOKE':continue
    with p.open('rb') as f:prefix=f.read(32768)
    marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
    if pos<0:continue
    names=[n.lower() for n in re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)]
    dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);offset=pos+len(marker)
    rec=np.memmap(p,mode='r',offset=offset,dtype=dtype,shape=((p.stat().st_size-offset)//dtype.itemsize,))
    end=np.flatnonzero(np.diff(rec['time'])<0);r=rec[:end[0]+1] if len(end) else rec
    c={n:r['v'][:,i] for i,n in enumerate(names[1:])};t=r['time']
    trip=c['v(trip_cota)']>.5;hits=np.flatnonzero(trip)
    if not len(hits):continue
    first=int(hits[0]);mask=(t>=max(0,t[first]-.0001))&(t<=t[first])
    print(json.dumps(dict(arquivo=p.stem,primeiro_trip_ms=float(t[first]*1e3),erro_ao_trip_uA=float(c['v(erro_cota)'][first]*1e6),
                         idade_ao_trip_us=float(c['v(idade_cota)'][first]*1e6),
                         erro_max_100us_uA=float(c['v(erro_cota)'][mask].max()*1e6))))
