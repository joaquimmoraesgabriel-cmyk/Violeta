"""Revisao com maior amplitude de entrada; preserva os ensaios anteriores."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
base=(ROOT/'MLC_base.inc').read_text(encoding='utf-8')
base=base.replace('entrada_amp=0.002 bias=-0.002','entrada_amp=0.005 bias=-0.005')
(ROOT/'MLC_base_v2.inc').write_text(base,encoding='utf-8')
for name in ('MLC_AND_sequencia','MLC_AND_validacao','MLC_AND_pilar_validacao','MLC_AND_pilar_demo'):
    source=(ROOT/(name+'.cir')).read_text(encoding='utf-8')
    source=source.replace('MLC_base.inc','MLC_base_v2.inc')
    (ROOT/(name+'_v2.cir')).write_text(source,encoding='utf-8')
print('Revisao 2: entrada de 0.005 por bit, bias=-0.005, mesmas janelas e perturbacoes.')
