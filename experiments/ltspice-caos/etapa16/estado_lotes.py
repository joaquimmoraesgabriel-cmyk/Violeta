"""Progresso de arquivos de simulacao; nao certifica resultados parciais."""
from pathlib import Path
import json
import re
import struct
import sys

ROOT=Path(__file__).resolve().parent
items=[]
arguments=[a for a in sys.argv[1:] if a!='--compact']
if not arguments:arguments=[p.name for p in ROOT.glob('lotes_*.json')]
for manifest in arguments:
    for name in json.loads((ROOT/manifest).read_text()):
        log=ROOT/f'{name}.log'
        txt=log.read_text(errors='replace') if log.exists() else ''
        item=dict(arquivo=name,passos_iniciados=len(re.findall(r'^\.step caso',txt,re.M)),completo='Measurement: pico_orcamento' in txt)
        raw=ROOT/f'{name}.raw'
        if raw.exists() and raw.stat().st_size:
            with raw.open('rb') as stream:
                prefix=stream.read(32768);marker='Binary:\n'.encode('utf-16-le');pos=prefix.find(marker)
                if pos<0:
                    marker='Binary:\r\n'.encode('utf-16-le');pos=prefix.find(marker)
                if pos>=0:
                    header=prefix[:pos].decode('utf-16-le')
                    n=int(re.search(r'No. Variables:\s*(\d+)',header)[1])
                    offset=pos+len(marker);size=raw.stat().st_size;stride=8+4*(n-1)
                    count=(size-offset)//stride
                    if count>0:
                        stream.seek(offset+(count-1)*stride)
                        item['ultimo_tempo_gravado_s']=struct.unpack('<d',stream.read(8))[0]
        items.append(item)
if '--compact' in sys.argv:
    done=[i for i in items if i['completo']]
    active=[i for i in items if not i['completo'] and i['passos_iniciados']]
    print(json.dumps(dict(decks_concluidos=len(done),trajetorias_concluidas=sum(len(json.loads((ROOT/(i['arquivo']+'.json')).read_text())) for i in done),
                         decks_total=len(items),ativos=active,na_fila=len(items)-len(done)-len(active))))
else:
    for item in items:print(json.dumps(item))
