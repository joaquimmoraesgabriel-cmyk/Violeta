"""Agrupa curvas reais para o guia; preserva os extremos de cada agrupamento."""
from pathlib import Path
import csv
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parent
TARGET=Path(r'C:\Users\joaqu\.codex\visualizations\2026\10\11\01a12ce4-de40-7793-86b4-bc7af4378136\entender-caos.html')
SEQUENCE=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
raw=(ROOT/'MLC_coordenador_demo.raw').read_bytes()
marker='Binary:\n'.encode('utf-16-le'); offset=raw.find(marker)
if offset<0:
    marker='Binary:\r\n'.encode('utf-16-le'); offset=raw.find(marker)
if offset<0:
    raise RuntimeError('Formato RAW desconhecido.')
header=raw[:offset].decode('utf-16-le')
names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',header,re.M)
count=int(re.search(r'No. Points:\s*(\d+)',header).group(1))
dtype=np.dtype([('time','<f8'),('values','<f4',(len(names)-1,))])
records=np.frombuffer(raw,offset=offset+len(marker),dtype=dtype,count=count)
parts=np.split(records,np.flatnonzero(np.diff(records['time'])<0)+1)
if len(parts)!=3:
    raise RuntimeError('Esperadas tres politicas.')
measurements=list(csv.DictReader((ROOT/'resultados_etapa7.csv').open(encoding='utf-8-sig')))
measurements=[row for row in measurements if row['arquivo']=='MLC_coordenador_demo.log']
data={'names':['Desligado','Divisão fixa','Coordenador'],'windows':[],'defaultPolicy':2,'defaultWindow':0}
failed=[row for row in measurements if row['politica']=='1' and row['acerto_persistente']=='0']
if failed:
    data['defaultWindow']=int(failed[0]['janela'])
xcol=names.index('V(x)')-1
scol=names.index('V(saida)')-1
for index,code in enumerate(SEQUENCE):
    window={'A':code//2,'B':code%2,'expected':int(code==3),'start':index*50,'readStart':index*50+30,'readEnd':index*50+49,'end':(index+1)*50,'runs':[]}
    for policy,part in enumerate(parts):
        mask=(part['time']>=index*0.05)&(part['time']<=(index+1)*0.05)
        selected=part[mask]
        bins=np.clip(((selected['time']-index*0.05)/0.000125).astype(int),0,399)
        points=[]
        for bin_index in np.unique(bins):
            chunk=selected[bins==bin_index]
            sample=chunk[len(chunk)//2]
            values=chunk['values']
            points.append([round(float(sample['time']*1000),4),round(float(sample['values'][xcol]),4),round(float(values[:,xcol].min()),4),round(float(values[:,xcol].max()),4),int(sample['values'][scol]>.5),int(values[:,scol].min()>.5),int(values[:,scol].max()>.5)])
        measurement=next(row for row in measurements if int(row['politica'])==policy and int(row['janela'])==index)
        window['runs'].append({'points':points,'passed':measurement['acerto_persistente']=='1','margin':round(float(measurement['margem']),5)})
    data['windows'].append(window)
text=TARGET.read_text(encoding='utf-8')
replacement=json.dumps(data,separators=(',',':'),ensure_ascii=False)
text=re.sub(r'(<script type="application/json" id="chaos-data7">).*?(</script>)',lambda match:match.group(1)+replacement+match.group(2),text,flags=re.S)
TARGET.write_text(text,encoding='utf-8')
if TARGET.stat().st_size>=1000000:
    raise RuntimeError('Guia excedeu limite de tamanho.')
print(f'Guia atualizado com curvas reais e medidas do LTspice: {TARGET.stat().st_size} bytes.')
