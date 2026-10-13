"""Atualiza a trilha de pesquisa com a evidencia final, sem apagar etapas anteriores."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
comp=json.loads((ROOT/'comparacoes.json').read_text(encoding='utf-8'))
ss={s['arquivo']:s for s in json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))}
v=json.loads((ROOT/'verificacao_entrega.json').read_text(encoding='utf-8'))
b,e,d=comp['familias'].values()
text=f'''## Etapa 16 — reserva local E dedicada a D

Foram concluidas {v['trajetorias_novas']} trajetorias novas no LTspice, alem da reanalise de 16 referencias corrigidas da etapa 15. Com o mesmo orcamento operacional de 90 uA, E revisado acertou {e['acertos']}/272 janelas de alta demanda, a referencia {b['acertos']}/272 e a prioridade em D com dois atuadores {d['acertos']}/272. E reduziu o residuo RMS da compensacao de D de {b['rms_d']:.3f} para {e['rms_d']:.3f} uA, mas o residuo do canal A-B-C passou de {b['rms_y']:.3f} para {e['rms_y']:.3f} uA. A variacao de g(x) ficou em {b['variacao_g']:.2f}/{e['variacao_g']:.2f} V/s do modelo (referencia/E); isso nao equivale a estresse termico.

As divergencias entre 1,25 e 0,625 us foram {b['divergencias']}/136 na referencia e {e['divergencias']}/136 em E. O terceiro passo de 0,3125 us ainda apresentou falhas. A reserva fixa de 20 uA ficou em {ss['E_fixo_f0']['corretas']}/68 sem falha do topo. Uma cota exploratoria de E de 5 uA ficou em {ss['E_cota5_f0']['corretas']}/68, contra 51/68 da referencia saudavel; esse ajuste nao foi expandido a todas as falhas ou ao terceiro passo.

A corrente passou nas {v['trajetorias_novas']} trajetorias novas pelas tres leituras, com pico pelos shunts de {v['pico_corrente_uA']:.6f} uA. A checagem previa encontrou uma inconsistência de cota na primeira reserva livre; a versao v2 a corrigiu, preservando os pilotos. Com perturbacoes em 75% e 50% da intensidade original, a referencia passou em {ss['C_demanda75']['corretas']}/68 e {ss['C_demanda50']['corretas']}/68. Isso delimita uma faixa mais favoravel, mas nao resolve o requisito de alta demanda original.

E tem nove leituras comportamentais e mediana explicita, ligadas apenas a sua funcao local de apoio a D. O comando E nao passa pelo topo; alimentacao e limitador continuam compartilhados. A saturacao utilizada e a falta de cota para atender D, nao uma falha fisica identificada no amplificador. A proposta completa tem 45 subpilares (5 x 9); A/B/C/D ainda usam replicas unicas neste lote. O conjunto de 45, o seletor adaptativo e chips/PCB permanecem por validar.

Manter E como candidato de reserva especializada, sem incorpora-lo como solucao aprovada para a alta demanda. O proximo foco e estudar a reparticao entre os estados x/y e a capacidade necessaria para preservar margem logica, com validacao em passos menores e condicoes novas. A referencia com dois atuadores continua disponivel. Relatorio: etapa16/ETAPA16_RESULTADOS.txt; grafico: etapa16/comparacao_pilar_E.svg; resultados completos e verificacao: etapa16/trajetorias.json, etapa16/janelas.csv e etapa16/verificacao_entrega.json.
'''
for filename in ['PIRAMIDE_CANDIDATA.md','PESQUISA_HIPOTESE_PILARES.md']:
    path=ROOT.parent/filename
    original=path.read_text(encoding='utf-8')
    marker='\n## Etapa 16 — reserva local E dedicada a D\n'
    if marker in original:original=original.split(marker)[0].rstrip()+'\n'
    path.write_text(original.rstrip()+'\n\n'+text,encoding='utf-8')
print('Trilha de pesquisa atualizada nos dois documentos existentes.')
