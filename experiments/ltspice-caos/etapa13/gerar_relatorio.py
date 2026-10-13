"""Relatorio final da alternativa combinada, preservando ensaios anteriores."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
S = json.loads((ROOT / 'resumo_ampliado.json').read_text())
T = json.loads((ROOT / 'trajetorias_ampliadas.json').read_text())
OLD = json.loads((ROOT / 'resumo.json').read_text())
NAMES = ['Equilibrado', 'AB exige mais', 'CD exige mais', 'Todos exigem']
FAULTS = ['Sem falha', 'Parou e perdeu heartbeat', 'Atraso permanente de 500 µs', 'Sinal invertido', 'Parou com heartbeat mantido']

def get(architecture, profile, fault=0):
    return next(r for r in S if r['arquitetura'] == architecture and r['perfil'] == profile and r['falha'] == fault)

main = ['| Perfil | Quatro atuadores | Dois combinados | Quatro: passam nos dois passos | Dois: passam nos dois passos |',
        '|---|---|---|---|---|']
detail = ['| Perfil | Arquitetura | Passo 2,5 µs | Passo 1,25 µs | Classificações alteradas |', '|---|---|---|---|---|']
for p in range(4):
    a, b = get('separados', p), get('combinados', p)
    main.append(f"| {NAMES[p]} | {a['corretas']}/68 | {b['corretas']}/68 | {a['corretas_ambos_passos']}/34 | {b['corretas_ambos_passos']}/34 |")
    for r in [a, b]:
        detail.append(f"| {NAMES[p]} | {r['arquitetura']} | {r['corretas_passo_2_5']}/34 | {r['corretas_passo_1_25']}/34 | {r['classificacoes_alteradas']} |")

fault = ['| Falha do topo, perfil AB | Quatro atuadores | Dois combinados | Quatro: passam nos dois passos | Dois: passam nos dois passos |',
         '|---|---|---|---|---|']
for f in range(5):
    a, b = get('separados', 1, f), get('combinados', 1, f)
    fault.append(f"| {FAULTS[f]} | {a['corretas']}/68 | {b['corretas']}/68 | {a['corretas_ambos_passos']}/34 | {b['corretas_ambos_passos']}/34 |")

diagnostics = ['| Arquitetura | Acertos sem falha | Trajetórias completas sem falha | Pico das correntes salvas (µA) | Casos fora do critério |',
               '|---|---|---|---|---|']
for architecture in ['separados', 'combinados']:
    selected = [r for r in S if r['arquitetura'] == architecture and r['falha'] == 0]
    trajectories = [r for r in T if r['arquitetura'] == architecture]
    diagnostics.append(f"| {architecture} | {sum(r['corretas'] for r in selected)}/272 | {sum(r['trajetorias_inteiras'] for r in selected)}/16 | {max(r['pico_correntes_uA'] for r in trajectories):.9f} | {sum(r['fora_tolerancia_correntes'] for r in trajectories)}/32 |")

prior = ['| Primeiro ensaio, sem sondas de corrente | Comum | Combinado |', '|---|---|---|']
for p in [0, 3]:
    counts = [sum(r['corretas'] for r in OLD if r['arquivo'] == name and r['perfil'] == p) for name in ['COMB_comum', 'COMB_combinado']]
    prior.append(f'| {NAMES[p]} | {counts[0]}/68 | {counts[1]}/68 |')

totals = {architecture: sum(r['corretas'] for r in S if r['arquitetura'] == architecture and r['falha'] == 0)
          for architecture in ['separados', 'combinados']}
interpretation = f"Nos ensaios sem falha, quatro atuadores acertaram {totals['separados']}/272 janelas e dois combinados {totals['combinados']}/272. No perfil de maior demanda, foram {get('separados', 3)['corretas']}/68 e {get('combinados', 3)['corretas']}/68, respectivamente. Sob atraso do topo, foram {get('separados', 1, 2)['corretas']}/68 e {get('combinados', 1, 2)['corretas']}/68; sob parada com perda de heartbeat, {get('separados', 1, 1)['corretas']}/68 e {get('combinados', 1, 1)['corretas']}/68. A soma melhora algumas condições e piora outras. Não há vantagem uniforme de tolerância a falhas."

report = '''# Etapa 13: combinar correções antes de repartir a capacidade

A/B/C estimam desvios distintos, mas os três corrigem a equação do mesmo estado y. Podemos somar seus pedidos com os sinais corretos antes da limitação e usar um atuador bidirecional em y. D continua com atuação em x. Esta comparação preserva as quatro funções de estimação e muda a arquitetura de atuação: quatro fontes independentes versus duas fontes com pedidos combinados.

Na referência, o ganho h é calculado a partir de |d_A|+|d_B|+|d_C|+|d_D|; as correntes resultantes são I_y=h*(d_A-d_B-d_C) e I_x=h*d_D. Na alternativa, primeiro calculamos d_y=d_A-d_B-d_C; o ganho passa a considerar |d_y|+|d_D| para aplicar dois comandos sob 100 µA. Correntes em x e y continuam contadas em módulo separadamente. Não usamos a resposta AND esperada para controlar os atuadores.

Por exemplo, pedidos de A=+40 µA, B=+35 µA e C=0 resultam em +5 µA em y, pois B tem sentido oposto a A na equação. Quatro atuadores gastariam 75 µA de capacidade de atuação nesse par antes de somar seus efeitos; um atuador combinado pede 5 µA. Isso é uma diferença de capacidade de corrente no modelo, não uma medida de energia poupada.

```mermaid
flowchart LR
    A[Estimativa A: amortecimento] --> Y[Soma assinada A-B-C]
    B[Estimativa B: bias] --> Y
    C[Estimativa C: excitação] --> Y
    D[Estimativa D: curva não linear] --> K[Coordenador de 100 µA]
    Y --> K
    K --> AY[Atuador em y]
    K --> AX[Atuador em x]
    AY --> P[Porta MLC]
    AX --> P
```

## Comparação ampliada

64 trajetórias, 1088 janelas: 32 trajetórias sem falha e 32 com falha. As arquiteturas usam os mesmos quatro perfis da etapa 12, x inicial=-0,37/+0,37, y=-0,2, passos máximos 2,5 e 1,25 µs, reltol=1e-6, vntol=1e-11 e abstol=1e-12. Cada perfil por arquitetura tem quatro trajetórias e 68 janelas; o requisito de passar nos dois passos tem 34 janelas pareadas. Não se somam quatro perfis de uma arquitetura com resultados de outra precisão.

Mesmos erros, latência de 50 µs e filtro de 100 µs dos sensores anteriores. São réplicas contínuas; os quatro grupos de nove sensores adaptativos ainda não foram integrados. Todos mantêm a proteção que rejeita comando de sinal oposto ao pedido atual e limita a soma restante. Com atuador combinado, a verificação de sinal usa o pedido líquido em y; na referência, usa cada pedido individual.

Cada atuador contém uma sonda ideal de 0 V em série. Além do monitor interno, somamos as correntes salvas dessas sondas fora do LTspice, no mesmo instante. A capacidade nominal é 100 µA; o critério de verificação numérica é 100,005 µA. Os logs devem ter as 17 janelas completas e cada RAW chegar a 0,85 s.

''' + '\n'.join(main) + '\n\n' + '\n'.join(diagnostics) + '''

## Sensibilidade ao passo

''' + '\n'.join(detail) + '''

Estas são contagens determinísticas dos ensaios. Alterações de classificação mostram sensibilidade numérica. Nem a soma dos dois passos nem passar em ambos prova convergência contínua, confiabilidade física ou probabilidade de sucesso. Os casos foram herdados de ensaios já conhecidos; este é um estudo de arquitetura e não um conjunto independente de seleção.

## Falhas do topo

As falhas 1, 3 e 4 duram de 343,35 a 403,35 ms; a falha 2 introduz atraso permanente de 500 µs nos comandos. Todas afetam o topo inteiro e seus atuadores em ambas as arquiteturas. Assim, a extensão compara o mesmo domínio de falha, diferentemente das falhas locais de grupo da etapa 12. O combinado não tem reserva local e não diagnostica o heartbeat; nas falhas 1 e 4, seu comando de atuação é zero nos dois casos.

''' + '\n'.join(fault) + '''

## Primeiro ensaio preservado

Antes da queda de conexão, já havia 24 trajetórias e 408 janelas completas em COMB_comum, COMB_combinado e COMB_falhas. A comparação sem falha cobria dois perfis e a falha do combinado cobria o perfil AB em passo 2,5 µs. Os resultados, modelos, logs, RAW e manifestos antigos foram preservados em resultados.csv e resumo.json; a extensão usa arquivos separados.

''' + '\n'.join(prior) + '''

O primeiro ensaio acusou dois picos do monitor do comum acima de 100,005 µA. Esses arquivos não salvavam separadamente as correntes dos atuadores, portanto não sustentam uma verificação independente da corrente aplicada. A conferência da etapa 12 demonstrou uma discrepância entre monitor e correntes em oito casos repetidos; ela não corrige automaticamente todos os outros logs históricos. A extensão acima utiliza sondas e soma externa.

## Interpretação e próximos critérios

A combinação elimina a disputa de capacidade entre pedidos opostos no mesmo estado. Não elimina erro compartilhado de sensores, saturação quando o pedido líquido excede o limite, falha do coordenador nem os atrasos dos comandos. Um atuador compartilhado também concentra a falha de atuação de A/B/C: não testamos perda, travamento, alimentação ou limitação individual desse atuador. Não estimamos custo, consumo ou área de componentes reais, nem reestimamos Lyapunov em todos estes casos.

O comum foi a melhor referência entre as cinco regras da etapa 12 sem falha. A soma é uma alternativa de atuação a comparar com essa referência; nenhuma contagem com falhas autoriza chamar a arquitetura de plenamente confiável. O passo seguinte da pesquisa deve usar casos novos, um limitador físico e detecção por discrepância entre pedido e atuação, antes de integrar os quatro grupos adaptativos.

## Reprodução e arquivos

Primeiro ensaio: preparar_combinacao.py e lotes.json. Extensão: preparar_conferencia_ampliada.py e lotes_ampliados.json; executar.ps1 -Manifest lotes_ampliados.json, dividindo o lote com Slot=0/1 e Slots=2 se desejado. analisar_conferencia_ampliada.py valida os logs e RAW; gerar_relatorio.py produz este documento. resultados_ampliados.csv tem todas as janelas, trajetorias_ampliadas.json registra correntes e pedidos, e resumo_ampliado.json guarda as contagens pareadas. A conferência independente anterior está em ../etapa12/MEDICAO_CORRENTE.md.
'''
report = report.replace('## Interpretação e próximos critérios\n\n', '## Interpretação e próximos critérios\n\n' + interpretation + '\n\n')
(ROOT / 'ETAPA13_RESULTADOS.md').write_text(report, encoding='utf-8')
print('Relatorio ampliado salvo: 64 trajetorias, 1088 janelas.')
