"""Limita erro negativo para evitar saturacao ociosa do amplificador de limite."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
model = (ROOT / 'atuadores_intertravados.inc').read_text()
model = model.replace('Xlim soma ref vp vm limite level2', 'Bexcesso excesso 0 V={max(V(soma)-V(ref),0)}\nXlim excesso 0 vp vm limite level2')
(ROOT / 'atuadores_antiwindup.inc').write_text(model, encoding='utf-8')
text = (ROOT / 'BANCADA_intertravado.cir').read_text().replace('atuadores_intertravados.inc', 'atuadores_antiwindup.inc')
(ROOT / 'BANCADA_antiwindup.cir').write_text(text, encoding='utf-8')
ref = text.replace('.tran 0 400u 0 100n uic', '.tran 0 400u 0 5n uic').replace('threads=1', 'threads=1 method=gear')
(ROOT / 'BANCADA_antiwindup_ref.cir').write_text(ref, encoding='utf-8')
print('Bancadas sem saturacao negativa desnecessaria, mantendo a realimentacao de corrente.')
