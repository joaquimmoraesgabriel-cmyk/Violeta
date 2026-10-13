"""Preserva bancada original e testa isolamento RC durante partida."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
text = (ROOT / 'BANCADA_limite.cir').read_text()
text = text.replace('.include atuadores_candidatos.inc', '.include atuadores_intertravados.inc')
text = text.replace('XY cmd_y y vp vm med_y ATUADOR', 'XY cmd_y y vp vm med_y habilitado ATUADOR')
text = text.replace('XX cmd_x x vp vm med_x ATUADOR', 'XX cmd_x x vp vm med_x habilitado ATUADOR')
text = text.replace('XL med_y', 'Rstart vp partida 100k\nCstart partida 0 100p IC=0\nBready habilitado 0 V={if(V(partida)>3,if(V(vp)>4,1,0),0)}\nXL med_y')
text = text.replace('.save V(total)', '.save V(habilitado) V(total)')
(ROOT / 'BANCADA_intertravado.cir').write_text(text, encoding='utf-8')
ref = text.replace('.tran 0 400u 0 100n uic', '.tran 0 400u 0 5n uic').replace('threads=1', 'threads=1 method=gear')
(ROOT / 'BANCADA_intertravado_ref.cir').write_text(ref, encoding='utf-8')
print('Bancadas de partida protegida, passos 100 ns/trap e 5 ns/gear.')
