"""Consolida a matriz original, os controles, a auditoria e a correcao."""
from pathlib import Path
import json
from gerar_relatorio import main as base_report

ROOT=Path(__file__).resolve().parent

def main():
    original=json.loads((ROOT/'trajetorias.json').read_text())
    controls=json.loads((ROOT/'ablacao_trajetorias.json').read_text())
    audit=json.loads((ROOT/'auditoria_diagnostico.json').read_text())
    corrected=json.loads((ROOT/'filtros_trajetorias.json').read_text())
    assert (len(original),len(controls),len(audit),len(corrected))==(64,8,4,28)
    base_report()
    ab=[t for t in corrected if t['hardware'] and t['perfil']==1]
    high=[t for t in corrected if t['hardware'] and t['perfil']==3]
    peak=max(t['pico_tensoes_uA'] for t in corrected)
    alarms=sum(t['alarme_indevido'] for t in corrected)
    ideal=[t for t in corrected if not t['hardware']]
    lead=f'''## Conclusão da etapa e versão candidata

A Etapa 15 identificou e corrigiu uma assimetria entre os filtros da referência e da medição. A referência tinha RCs em cascata sem isolamento; o segundo carregava o primeiro. A auditoria reproduziu um alarme com atuador ideal: a corrente seguia o comando filtrado em -2,459593 µA, mas o primeiro filtro da referência marcava -5,138084 µA, com comandos de entrada praticamente iguais. Não era necessário aumentar os limiares do detector.

A correção acrescentou seguidores ideais entre os RCs da referência. Na regressão de 28 trajetórias: {alarms} alarmes indevidos; pico pelos shunts {peak:.6f} µA; {sum(t['corrente_falha_tensoes'] for t in corrected)} violações do teto de 100,005 µA. Com atuação não ideal, AB saudável/silencioso acertou {sum(t['corretas'] for t in ab)}/{len(ab)*17}; alta demanda saudável/silenciosa/atrasada/invertida, {sum(t['corretas'] for t in high)}/{len(high)*17}. O controle ideal de 90 µA após a correção acertou {sum(t['corretas'] for t in ideal)}/{len(ideal)*17}.

O candidato para continuar é `MLC_filtros_isolados.inc`. Esta regressão não repete toda a matriz original: cobre AB saudável/silencioso, quatro condições de alta demanda e um controle ideal. Os resultados anteriores à correção permanecem nas tabelas abaixo. Corrigir os alarmes não equivale a resolver a lógica em alta demanda.

Detalhes: [correção e regressão dos filtros](CORRECAO_FILTROS.md), [controle de capacidade](CONTROLE_CAPACIDADE.md). Foram concluídas 104 trajetórias válidas (1.768 janelas): 64 da matriz inicial, oito controles, quatro auditorias e 28 da correção. Não são 104 condições independentes; incluem repetições e comparações pareadas.

## Decisão para o próximo lote

Manter o alvo de 90 µA e a referência corrigida. Investigar primeiro a margem lógica em alta demanda: separar atraso/erro das estimativas da restrição de capacidade, variar a intensidade das perturbações e repetir os casos críticos com passo menor. Os controles de atuação ideal sem a correção dos filtros deram 50/68 a 90 µA e 56/68 a 100 µA; usar toda a capacidade nominal não eliminou as falhas. Qualquer nova estratégia deve preservar o teto e ser comparada com a versão corrigida sob as mesmas condições.

Depois, substituir os seguidores, a medida e os atuadores por circuitos de componentes específicos, verificando largura de banda, offset, faixa de tensão, estabilidade e alimentação. A correção introduziu um seguidor ideal; sua implementação real ainda exige caracterização. Só então incluir interconexões e térmica na placa virtual.

'''
    path=ROOT/'ETAPA15_RESULTADOS.md'
    body=path.read_text(encoding='utf-8')
    title,rest=body.split('\n',1)
    rest=rest.replace('## Resultado com reserva','## Matriz original antes da correção — resultado com reserva',1)
    path.write_text(title+'\n\n'+lead+rest.lstrip(),encoding='utf-8')
    info='''
## Auditoria e alterações posteriores à matriz inicial

As quatro repetições AUD_circuito/AUD_ideal90 salvaram os filtros internos. auditoria_diagnostico.json e AUD_*_caso*_evento.csv registram a diferença de caminho. Os preparadores inicialmente emitiram uma varredura de um único ponto, rejeitada pelo LTspice antes de simular. O formato foi corrigido para dois passos; os dois logs *.erro_preparacao.log foram preservados e não entram na contagem de trajetórias válidas.

preparar_correcao_filtros.py gera a correção e as 28 trajetórias; executar.ps1 com lotes_filtros.json as executa; analisar_correcao.py compara os resultados. analisar_auditoria.py gera o diagnóstico das quatro repetições. gerar_fechamento.py consolida os quatro conjuntos após suas análises. O modelo original da Etapa 14 não foi sobrescrito.
'''
    with path.open('a',encoding='utf-8') as stream:stream.write(info)
    print(json.dumps(dict(total_trajetorias=104,total_janelas=1768,corrigidas=28,alarmes_indevidos=alarms,
                          pico_corrigido_uA=peak,ab_corretas=sum(t['corretas'] for t in ab),
                          alta_corretas=sum(t['corretas'] for t in high),ideal_corretas=sum(t['corretas'] for t in ideal)),indent=2))

if __name__=='__main__':main()
