"""Acompanhamento RAW aproximado; resultados finais usam exclusivamente .meas."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
out=[]
for path in sorted(ROOT.glob('COORD_*.raw')):
    if path.name.endswith('.log.raw') or 'verificacao' in path.name:continue
    with path.open('rb') as f:prefix=f.read(16384)
    marker='Binary:\n'.encode('utf-16-le');off=prefix.find(marker)
    if off<0:marker='Binary:\r\n'.encode('utf-16-le');off=prefix.find(marker)
    if off<0:continue
    head=prefix[:off].decode('utf-16-le');names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',head,re.M)
    dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]);start=off+len(marker)
    count=(path.stat().st_size-start)//dtype.itemsize
    if count<=0:continue
    rec=np.memmap(path,mode='r',offset=start,dtype=dtype,shape=(count,))
    cuts=np.r_[0,np.flatnonzero(np.diff(rec['time'])<0)+1,len(rec)]
    cs=json.loads(path.with_suffix('.json').read_text())
    xcol=names.index('V(x)')-1
    for idx in range(len(cuts)-1):
        p=rec[cuts[idx]:cuts[idx+1]]
        if idx>=len(cs) or p[-1]['time']<.849999:continue
        correct=0;margins=[]
        for i,code in enumerate(SEQ):
            vals=p['v'][:,xcol][(p['time']>=i*.05+.03)&(p['time']<=(i+1)*.05-.001)]
            if not len(vals):break
            margin=float(vals.min()) if code==3 else -float(vals.max());margins.append(margin);correct+=int(margin>0)
        if len(margins)==17:
            c=cs[idx]
            out.append({'arquivo':path.stem,'perfil':c['perfil'],'politica':c['politica_coord'],'falha':c['falha_coord'],'passo_us':c['passo']*1e6,'x_inicial':c['x_inicial'],'acertos_RAW_aproximados':correct,'margem_RAW':min(margins)})
    del rec
(ROOT/'parcial_RAW.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
