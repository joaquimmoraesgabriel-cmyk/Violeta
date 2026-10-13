"""Bancada do candidato: tolerancia de shunt, offset e velocidade do atuador."""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
cases = [{'caso': i, 'erro_shunt': r, 'vos_teste': offset, 'gbw_teste': bw}
         for i, (r, offset, bw) in enumerate((r, o, b) for r in [-.01, .01] for o in [-100e-6, 100e-6] for b in [1e6, 2e6])]
source = (ROOT / 'BANCADA_filtrado_ref.cir').read_text()
lines = [line for line in source.splitlines() if not line.startswith(('.param margem_limite', '.param gbw_limit', '.param tau_cmd'))]
text = '\n'.join(lines).replace('atuadores_antiwindup.inc', 'atuadores_etapa14.inc')
tables = '\n'.join(f'.param {key}=table(caso,' + ','.join(f'{i},{c[key]}' for i, c in enumerate(cases)) + ')'
                   for key in ['erro_shunt', 'vos_teste', 'gbw_teste'])
text = text.replace('.param caso=0', '.param caso=0\n.param margem_limite=90u gbw_limit=100Meg tau_cmd=2u\n' + tables)
text = text.replace('habilitado ATUADOR', 'habilitado ATUADOR erro_r={erro_shunt} voff={vos_teste} gbw={gbw_teste}')
(ROOT / 'BANCADA_tolerancias.cir').write_text(text + '\n', encoding='utf-8')
(ROOT / 'BANCADA_tolerancias.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
print('Oito ensaios: shunts +/-1%, offset +/-100 uV, atuador 1/2 MHz.')
