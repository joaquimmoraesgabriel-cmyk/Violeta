"""Estados e pedidos no primeiro alarme de cada canto saudavel."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
out=[]
for name in ['C_tolerancia_mais','C_tolerancia_menos']:
    cases=json.loads((ROOT/f'{name}.json').read_text(encoding='utf-8'))
    for index,(t,c) in enumerate(raw_steps(ROOT/f'{name}.raw',2,max_last_gaps=[r['passo'] for r in cases])):
        hit=np.flatnonzero(c['v(trip_cota)']>.5)[0]
        out.append(dict(arquivo=name,caso=index,tempo_ms=float(t[hit]*1000),
            estados={n:float(c[f'v({n})'][hit]) for n in ['incoerente','idade_invalida','quota_invalida','timer_cota']},
            pedidos_uA={n:float(c[f'v(demanda_{n})'][hit]*1e6) for n in ['y','d']},
            cotas_uA={n:float(c[f'v(q_msg_{n})'][hit]*1e6) for n in ['y','d']}))
(ROOT/'diagnostico_tolerancias.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
