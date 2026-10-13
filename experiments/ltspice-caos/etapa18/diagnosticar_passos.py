"""Passos efetivos no final gravado, para diagnostico de desempenho."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
for p in ROOT.glob('*.raw'):
    if p.stem=='SMOKE':continue
    with p.open('rb') as f:prefix=f.read(32768)
    marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
    if pos<0:continue
    header=prefix[:pos].decode('utf-16-le');n=int(re.search(r'No. Variables:\s*(\d+)',header)[1])
    off=pos+len(marker);dtype=np.dtype([('time','<f8'),('v','<f4',(n-1,))]);count=(p.stat().st_size-off)//dtype.itemsize
    take=min(count,5000)
    if take<2:continue
    r=np.memmap(p,mode='r',offset=off+(count-take)*dtype.itemsize,dtype=dtype,shape=(take,))
    dt=np.diff(r['time']);dt=dt[dt>0]*1e6
    print(json.dumps(dict(arquivo=p.stem,ultimo_s=float(r['time'][-1]),dt_mediano_us=float(np.median(dt)),dt_medio_us=float(np.mean(dt)),pontos_gravados=count,MB=round(p.stat().st_size/1e6))))
