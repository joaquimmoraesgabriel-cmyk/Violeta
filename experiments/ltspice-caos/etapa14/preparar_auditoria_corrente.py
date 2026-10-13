"""Auditar discrepancia de armazenamento de correntes no caso de atraso."""
from pathlib import Path
import json
from preparar_etapa14 import write
ROOT = Path(__file__).resolve().parent
cases = []
for detector in [0, 1]:
    original = json.loads((ROOT / f'DET_d{detector}_falha2.json').read_text())
    cases.extend(c for c in original if c['x_inicial'] == -.37)
cases = [dict(c, caso=i) for i, c in enumerate(cases)]
write('AUDIT_atraso', cases)
path = ROOT / 'AUDIT_atraso.cir'
text = path.read_text().replace('.tran 0', '.save V(n_y) V(br_y) V(n_d) V(br_d) I(RmedY) I(RmedD) I(Bcorrecao_y) I(Bcorrecao_d)\n.tran 0', 1)
path.write_text(text, encoding='utf-8')
phy = []
for fault in [0, 4]:
    phy.extend(c for c in json.loads((ROOT / f'PHY_d1_falha{fault}.json').read_text()) if c['x_inicial'] == -.37)
phy = [dict(c, caso=i) for i,c in enumerate(phy)]
write('AUDIT_circuito', phy, 'MLC_circuito_reserva.inc')
path = ROOT / 'AUDIT_circuito.cir'
text = path.read_text().replace('.tran 0', '.save V(xy:entrada_shunt) V(xd:entrada_shunt) V(br_y) V(br_d)\n.tran 0', 1)
path.write_text(text, encoding='utf-8')
(ROOT / 'lote_auditoria.json').write_text(json.dumps(['AUDIT_atraso','AUDIT_circuito']), encoding='utf-8')
print('Duas repeticoes adicionais com tensoes diretas nos shunts do circuito.')
print('Quatro repeticoes para conferir fontes, resistores, sondas e tensoes diretas.')
