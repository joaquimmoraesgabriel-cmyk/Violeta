"""Bancada curta para caracterizar limitador sem usar resposta logica."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
shutil.copyfile(Path('C:/Users/joaqu/AppData/Local/LTspice/lib/sub/UniversalOpAmp2.lib'), ROOT / 'UniversalOpAmp2.lib')
cases = []
for cap in [90e-6, 95e-6]:
    for gbw in [20e6, 100e6, 200e6]:
        cases.append({'caso': len(cases), 'margem_limite': cap, 'gbw_limit': gbw})
lines = ['* Bancada bidirecional; degraus e carga oscilante.', '.include atuadores_candidatos.inc', '.param caso=0']
for key in ['margem_limite', 'gbw_limit']:
    lines.append(f'.param {key}=table(caso,' + ','.join(f'{i},{c[key]}' for i, c in enumerate(cases)) + ')')
lines += ['.step param caso 0 5 1', 'Vp vp 0 5', 'Vm vm 0 -5',
          'VloadY y 0 SINE(0 1.4 1000)', 'VloadX x 0 SINE(0 1.2 730)',
          'VpedidoY pedido_y 0 PWL(0 0 20u 0 20.1u 40u 70u 40u 70.1u 250u 130u 250u 130.1u -250u 190u -250u 190.1u 0 230u 0 230.1u 80u 290u 80u 290.1u -80u 350u -80u 350.1u 0)',
          'VpedidoX pedido_x 0 PWL(0 0 20u 0 20.1u 40u 70u 40u 70.1u 250u 130u 250u 130.1u 250u 190u 250u 190.1u 0 230u 0 230.1u 10u 290u 10u 290.1u -10u 350u -10u 350.1u 0)',
          'BcmdY cmd_y 0 V={V(pedido_y)*V(ganho)}', 'BcmdX cmd_x 0 V={V(pedido_x)*V(ganho)}',
          'XY cmd_y y vp vm med_y ATUADOR', 'XX cmd_x x vp vm med_x ATUADOR',
          'XL med_y med_x vp vm ganho LIMITADOR',
          'Btotal total 0 V={abs(V(med_y))+abs(V(med_x))}',
          '.save V(total) V(ganho) V(med_y) V(med_x) I(VloadY) I(VloadX)',
          '.tran 0 400u 0 100n uic',
          '.meas tran pico MAX V(total) FROM 0 TO 400u',
          '.meas tran patamar AVG V(total) FROM 95u TO 125u',
          '.options plotwinsize=0 reltol=1e-6 vntol=1e-9 abstol=1e-12 threads=1', '.end']
(ROOT / 'BANCADA_limite.cir').write_text('\n'.join(lines) + '\n', encoding='utf-8')
ref = ('\n'.join(lines) + '\n').replace('.tran 0 400u 0 100n uic', '.tran 0 400u 0 5n uic').replace('threads=1', 'threads=1 method=gear')
(ROOT / 'BANCADA_limite_ref.cir').write_text(ref, encoding='utf-8')
(ROOT / 'BANCADA_limite.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
print('Seis ensaios curtos de limite, inversao e degrau, com modelo ADI de amplificador.')
