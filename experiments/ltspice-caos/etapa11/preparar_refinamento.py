from preparar_d import ROOT,deck
import json
cases=json.loads((ROOT/'MLC_D_validacao.json').read_text())
ref=[]
for c in cases:
    if c['perfil'] in [1,2] and c['passo']==1.25e-6:ref.append(dict(c,caso=len(ref),passo=.625e-6))
deck(ROOT,'MLC_D_refinamento','MLC_quatro_pilares.inc',ref)
print('Oito trajetorias de D em 0,625 us: forte isolado e quatro desvios.')
