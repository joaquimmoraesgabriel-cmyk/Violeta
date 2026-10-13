"""Confere a mediana nos dados RAW da demonstracao, independentemente do voto."""
from pathlib import Path
import json,re
import numpy as np
ROOT=Path(__file__).resolve().parent
raw=(ROOT/'MLC_subpilares_demo.raw').read_bytes()
marker='Binary:\n'.encode('utf-16-le');offset=raw.find(marker)
if offset<0: marker='Binary:\r\n'.encode('utf-16-le');offset=raw.find(marker)
if offset<0: raise ValueError('RAW desconhecido')
head=raw[:offset].decode('utf-16-le')
names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',head,re.M)
count=int(re.search(r'No. Points:\s*(\d+)',head).group(1))
records=np.frombuffer(raw,offset=offset+len(marker),dtype=np.dtype([('time','<f8'),('v','<f4',(len(names)-1,))]),count=count)
parts=np.split(records,np.flatnonzero(np.diff(records['time'])<0)+1)
if len(parts)!=3:raise ValueError('Esperados tres passos')
results=[]
for n,part in zip([1,3,9],parts):
    # O ponto inicial uic guarda zeros antes de avaliar as fontes; excluir t=0.
    part=part[part['time']>1e-9]
    ideal=.010*np.sin(2*np.pi*137*part['time']+np.deg2rad(40))-.0002
    measured=part['v'][:,names.index('V(estimativa_b)')-1]
    expected=ideal+(.02 if n==1 else 0)
    error=float(np.max(np.abs(measured-expected)))
    if error>1e-7:raise ValueError(f'Mediana divergiu do resultado independente: {n}, {error}')
    results.append({'nsub':n,'falhas':1,'maior_erro_RAW_vs_estimativa_prevista':error,'maior_desvio_estima_vs_sensor_saudavel':float(np.max(np.abs(measured-ideal)))})
(ROOT/'verificacao_mediana.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
