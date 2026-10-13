"""Testar rampa RC de comando sem substituir a limitacao por realimentacao."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
cases = [{'caso': i, 'margem_limite': cap, 'gbw_limit': bandwidth, 'tau_cmd': tau}
         for i, (cap, bandwidth, tau) in enumerate((cap, bw, tau) for cap in [90e-6, 95e-6]
                                                  for bw in [100e6, 200e6] for tau in [2e-6, 10e-6])]
text = (ROOT / 'BANCADA_antiwindup.cir').read_text()
lines = [line for line in text.splitlines() if not line.startswith(('.param margem_limite', '.param gbw_limit'))]
text = '\n'.join(lines).replace('.step param caso 0 5 1', '.step param caso 0 7 1')
tables = '\n'.join(f'.param {key}=table(caso,' + ','.join(f'{i},{c[key]}' for i, c in enumerate(cases)) + ')'
                   for key in ['margem_limite', 'gbw_limit', 'tau_cmd'])
text = text.replace('.param caso=0', '.param caso=0\n' + tables)
filters = '''BnormY norm_y 0 V={10000*V(pedido_y)}
BnormX norm_x 0 V={10000*V(pedido_x)}
RcmdY norm_y filtro_y 1000
CcmdY filtro_y 0 {tau_cmd/1000} IC=0
RcmdX norm_x filtro_x 1000
CcmdX filtro_x 0 {tau_cmd/1000} IC=0
BcmdY cmd_y 0 V={V(filtro_y)/10000*V(ganho)}'''
text = text.replace('BcmdY cmd_y 0 V={V(pedido_y)*V(ganho)}', filters)
text = text.replace('BcmdX cmd_x 0 V={V(pedido_x)*V(ganho)}', 'BcmdX cmd_x 0 V={V(filtro_x)/10000*V(ganho)}')
(ROOT / 'BANCADA_filtrado.cir').write_text(text + '\n', encoding='utf-8')
ref = text.replace('.tran 0 400u 0 100n uic', '.tran 0 400u 0 5n uic').replace('threads=1', 'threads=1 method=gear')
(ROOT / 'BANCADA_filtrado_ref.cir').write_text(ref + '\n', encoding='utf-8')
(ROOT / 'BANCADA_filtrado.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
print('Oito casos com filtro RC 2/10 us, patamar 90/95 uA e resposta 100/200 MHz.')
