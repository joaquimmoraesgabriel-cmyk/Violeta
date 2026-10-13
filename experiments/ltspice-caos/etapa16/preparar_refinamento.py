"""Terceiro passo e falhas de sensores E, escolhidos sem ajustar limiares."""
from preparar_etapa16 import ROOT,make
import json

jobs=[make('R_base',steps=(.3125e-6,)),
      make('R_E_v2','MLC_pilar_E_v2.inc',steps=(.3125e-6,)),
      make('R_rapido',steps=(.3125e-6,),lat_s=5e-6,tau_s=10e-6),
      make('E_quatro_falhas','MLC_pilar_E_v2.inc',steps=(.625e-6,),falhas_e=4),
      make('E_erro_comum','MLC_pilar_E_v2.inc',steps=(.625e-6,),erro_comum_e=.002)]
(ROOT/'lotes_refinamento.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
print('10 trajetorias: terceiro passo em tres candidatos e dois cenarios de erro em E.')
