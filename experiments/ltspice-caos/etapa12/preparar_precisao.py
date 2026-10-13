"""Refinamento motivado por pico de corrente acima da tolerancia, sem remover a falha."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import deck
model=(ROOT/'MLC_coordenadores_falhas.inc').read_text().replace('vntol=1e-9','vntol=1e-11')
(ROOT/'MLC_coordenadores_precisao.inc').write_text(model,encoding='utf-8')
original=json.loads((ROOT/'COORD_falha4_AB.json').read_text())
cases=[dict(c,caso=i) for i,c in enumerate(c for c in original if c['politica_coord'] in [0,2,4] and c['x_inicial']==-.37)]
deck(ROOT,'COORD_precisao','MLC_coordenadores_precisao.inc',cases)
(ROOT/'lote_precisao.json').write_text(json.dumps(['COORD_precisao']),encoding='utf-8')
print('Tres repeticoes de precisao: comum, emprestimo e reserva; mesma condicao e passo.')
