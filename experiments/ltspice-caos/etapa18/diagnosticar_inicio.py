"""Contexto da demanda no primeiro alarme, lendo apenas o inicio do RAW."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
rows=[]
for name in ['L2_5_10','L2_1_2','L2_5_10_v2']:
    p=ROOT/f'{name}.raw'
    if not p.exists():continue
    with p.open('rb') as f:prefix=f.read(32768)
    marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
    if pos<0:continue
    names=[n.lower() for n in re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)]
    dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);off=pos+len(marker)
    rec=np.memmap(p,mode='r',offset=off,dtype=dtype,shape=(min(50000,(p.stat().st_size-off)//dtype.itemsize),))
    c={n:rec['v'][:,i] for i,n in enumerate(names[1:])};hits=np.flatnonzero(c['v(trip_cota)']>.5)
    if not len(hits):print(name,': sem trip no inicio lido');continue
    i=int(hits[0]);y=abs(float(c['v(demanda_y)'][i]));dd=abs(float(c['v(demanda_d)'][i]))
    row=dict(arquivo=name,caso=0,tempo_us=float(rec['time'][i]*1e6),pedido_y_uA=y*1e6,pedido_d_uA=dd*1e6,
        total_pedido_uA=(y+dd)*1e6,cota_y_uA=float(c['v(q_msg_y)'][i])*1e6,cota_d_uA=float(c['v(q_msg_d)'][i])*1e6)
    rows.append(row);print(json.dumps(row))
(ROOT/'diagnostico_inicio.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
