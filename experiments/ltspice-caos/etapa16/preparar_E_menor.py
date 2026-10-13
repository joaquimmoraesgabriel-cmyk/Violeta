"""Ajuste exploratorio apos observar penalizacao de Y no controle de prioridade."""
from preparar_etapa16 import ROOT,make
import json
name=make('E_cota5_f0','MLC_pilar_E_v2.inc',cap_e=5e-6)
(ROOT/'lotes_E_menor.json').write_text(json.dumps([name]),encoding='utf-8')
(ROOT/'MOTIVO_E_MENOR.txt').write_text(
    'O primeiro controle de prioridade ficou em 48/68 janelas, contra 51/68 da referencia saudavel. '
    'O residuo RMS de D caiu de 21,225 para 13,362 uA, mas o de Y subiu de 40,748 para 49,433 uA. '
    'Isso motiva uma unica cota alternativa, 5 uA, para limitar o custo imposto a Y. '
    'Ensaio exploratorio: mesmos dois passos e estados iniciais, apenas topo saudavel. '
    'Nao juntar estas 68 janelas com falhas do modelo de 20 uA nem escolher a melhor semente.\n',encoding='utf-8')
print('Quatro trajetorias de E revisado com cota maxima de 5 uA.')
