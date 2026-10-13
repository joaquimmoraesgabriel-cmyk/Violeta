"""Indicadores provisórios de trajetorias ja gravadas ate 0.85 s; sem .meas final."""
from pathlib import Path
import json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
rows=[]
for manifest in ROOT.glob('lotes_*.json'):
    for name in json.loads(manifest.read_text(encoding='utf-8')):
        if len(sys.argv)>1 and name not in sys.argv[1:]:continue
        p=ROOT/f'{name}.raw'
        if not p.exists():continue
        with p.open('rb') as f:prefix=f.read(32768)
        marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
        if pos<0:continue
        names=[n.lower() for n in re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)]
        dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);off=pos+len(marker)
        rec=np.memmap(p,mode='r',offset=off,dtype=dtype,shape=((p.stat().st_size-off)//dtype.itemsize,))
        if not len(rec):continue
        cuts=np.r_[0,np.flatnonzero(np.diff(rec['time'])<0)+1,len(rec)]
        params=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
        for index,(a,b) in enumerate(zip(cuts[:-1],cuts[1:])):
            r=rec[a:b];t=r['time']
            if t[-1]<.85-params[index]['passo']-1e-12:continue
            c={n:r['v'][:,i] for i,n in enumerate(names[1:])};p0=params[index];x=c['v(x)']
            results=[]
            for j,code in enumerate([0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]):
                lo=j*.05+.03;hi=j*.05+.049;aa,bb=np.searchsorted(t,[lo,hi]);edge=np.interp([lo,hi],t,x)
                margin=min(x[aa:bb].min(),edge.min()) if code==3 else -max(x[aa:bb].max(),edge.max())
                results.append(bool(margin>0))
            start=0 if p0['falha_super'] in [2,5] else .34335
            trip=c['v(trip_cota)']>.5;before=(t>=.002)&((t<start) if p0['falha_super'] else True)
            physical=sum(np.abs((c[f'v(x{ch}:entrada_shunt)'].astype(float)-c[f'v(br_{ch})'].astype(float))/1000) for ch in ['y','d','e'])
            rows.append(dict(arquivo=name,caso=index,corretas=sum(results),falso=bool(np.any(trip&before)),
                primeiro_trip_ms=float(t[trip][0]*1e3) if np.any(trip) else None,pico_uA=float(physical.max()*1e6)))
(ROOT/'instantaneo_parcial.json').write_text(json.dumps(dict(provisorio=True,sem_conferencia_log=True,arquivos_solicitados=sys.argv[1:],trajetorias=rows),indent=2),encoding='utf-8')
for name in dict.fromkeys(r['arquivo'] for r in rows):
    part=[r for r in rows if r['arquivo']==name]
    print(json.dumps(dict(arquivo=name,percursos_gravados=len(part),corretas=sum(r['corretas'] for r in part),janelas=17*len(part),
        falsos=sum(r['falso'] for r in part),pico_uA=max(r['pico_uA'] for r in part))))
print(f'PROVISORIO: {len(rows)} trajetorias gravadas ate 0.85 s; aguardar logs e auditoria completa.')
