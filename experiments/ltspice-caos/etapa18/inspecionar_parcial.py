"""Amostra final dos RAWs em gravacao: diagnostico, NAO validacao."""
from pathlib import Path
import json,re,struct,sys
ROOT=Path(__file__).resolve().parent
for p in ROOT.glob('*.raw'):
    if p.stem=='SMOKE':continue
    if len(sys.argv)>1 and p.stem not in sys.argv[1:]:continue
    with p.open('rb') as f:
        prefix=f.read(32768);marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
        if pos<0:continue
        names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',prefix[:pos].decode('utf-16-le'),re.M)
        stride=8+4*(len(names)-1);offset=pos+len(marker);count=(p.stat().st_size-offset)//stride
        if count<1:continue
        f.seek(offset+(count-1)*stride);data=f.read(stride)
    if len(data)!=stride:continue
    vals=struct.unpack('<d'+'f'*(len(names)-1),data);d=dict(zip([n.lower() for n in names],vals))
    print(json.dumps(dict(arquivo=p.stem,tempo=round(d['time'],4),reserva=d['v(reserva_cota)'],trip=d['v(trip_cota)'],erro_uA=round(d['v(erro_cota)']*1e6,3),idade_us=round(d['v(idade_cota)']*1e6,3))))
