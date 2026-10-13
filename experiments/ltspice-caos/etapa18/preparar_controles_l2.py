"""Adendo motivado por falsos alarmes L2 no piloto; nao altera modelo em execucao."""
import json
from preparar_etapa18 import ROOT,make
jobs=[make('L2_20_50_off',politica_l2=1,diagnostico_cotas=0),
      make('L2_5_10_off',politica_l2=1,diagnostico_cotas=0,lat_coord=5e-6,tau_coord=10e-6)]
(ROOT/'lotes_controles_l2.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
(ROOT/'ADENDO_CONTROLES_L2.txt').write_text('''Adendo durante o piloto, antes destes oito ensaios completos.

Amostras parciais mostraram reserva de cotas acionada em L2 5/10 e 1/2 us
saudaveis. Portanto seus resultados apos comutacao nao isolam a regra L2.
Acrescentamos L2 20/50 e 5/10 us, ambos com atuacao do monitor desabilitada,
mesmo novo modelo/circuitos de observacao, dois passos e duas condicoes.
Total previsto passa de 48 para 56 trajetorias. Mantidos todos os ensaios
originais, inclusive os alarmes indevidos. Nao se ajustam limiares usando
a pontuacao logica. Os controles antigos da etapa17 serao so contexto.
''',encoding='utf-8')
print('Oito controles adicionais preparados; total 56.')
