"""Expansao predefinida: falhas do topo e reducao da perturbacao, sem calibrar em acertos."""
from preparar_etapa16 import ROOT,make,revised_models
import json

revised_models()
jobs=[]
for f in [0,4,2,3]:
    jobs += [make(f'E_v2_f{f}','MLC_pilar_E_v2.inc',fault=f),
             make(f'D_v2_f{f}','MLC_prioridade_D_v2.inc',fault=f)]
for factor in [.5,.75]:
    amps={f'amp_{c}':v*factor for c,v in zip('abcd',[.006,.009,.007,.008])}
    jobs.append(make(f'C_demanda{int(factor*100)}',**amps))
    if factor==.75:jobs.append(make('E_demanda75','MLC_pilar_E_v2.inc',**amps))
(ROOT/'lotes_expansao.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
print(f'{len(jobs)} decks, {len(jobs)*4} trajetorias adicionais.')
