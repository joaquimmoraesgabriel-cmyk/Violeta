from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
summary=json.loads((ROOT/'resumo_selecao.json').read_text())
main=[r for r in summary if r['passo_us']==5]
profiles=['saudaveis','uma_falha','quatro_falhas','erro_comum','ruido_alto']
policies=['nove_fixos','tres_fixos','rodizio','sorteio','adaptativo']
def get(profile,policy):return [r for r in main if r['perfil']==profile and r['politica']==policy]
table=[]
for p in profiles:
    cells=[]
    for policy in policies:
        rs=get(p,policy)
        cells.append('; '.join(f"{r['corretas']}/34" for r in rs) if policy=='sorteio' else f"{rs[0]['corretas']}/34")
    table.append('| '+p+' | '+' | '.join(cells)+' |')
aggregate=[]
for policy in policies:
    rs=[r for r in main if r['politica']==policy]
    aggregate.append(f"| {policy} | {sum(r['corretas'] for r in rs)}/{sum(r['janelas'] for r in rs)} | {sum(r['trajetorias_corretas'] for r in rs)}/{len(rs)*2} | {sum(r['media_ligados'] for r in rs)/len(rs):.3f} | {min(r['menor_margem'] for r in rs):.6f} |")
rows=list(csv.DictReader((ROOT/'resultados_selecao.csv').open(encoding='utf-8-sig')))
changes=[]
for r in rows:
    if 'original' not in r or not r['original']:continue
    m=next(m for m in rows if m['nome']==r['original'] and m['x_inicial']==r['x_inicial'] and m['janela']==r['janela'])
    if r['acerto']!=m['acerto']:changes.append({'nome':r['nome'],'x_inicial':r['x_inicial'],'janela':r['janela'],'acerto_5us':m['acerto'],'acerto_2_5us':r['acerto']})
(ROOT/'comparacao_refinamento.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
ref_table=[]
for r in summary:
    if r['passo_us']==2.5:
        m=next(m for m in main if m['nome']==r['original'])
        ref_table.append(f"| {r['perfil']} | {r['politica']} | {m['corretas']}/34 | {r['corretas']}/34 | {r['menor_margem']:.6f} |")
adapt=get('quatro_falhas','adaptativo')[0]
duty=adapt['media_ligados'];saving=(1-duty/9)*100
latencies=[f"{d['latencia_ms']:.3f}" if d['latencia_ms'] is not None else 'nao detectada' for d in adapt['deteccoes']]
usage=[]
for p in profiles:
    a=get(p,'adaptativo')[0]
    usage.append(f"| {p} | {a['media_ligados']:.3f} | {a['fracao_alarme_sem_falha']*100:.2f}% | {a['trocas_individuais']} |")
peak=max(r['pico_orcamento_uA'] for r in summary)
report=f'''# Etapa 9: escolher subpilares durante a operacao

O seletor adaptativo foi o melhor compromisso observado entre acertos e quantidade de participantes, nas condicoes avaliadas: com quatro falhas, manteve 34/34 janelas, como nove fixos, usando em media {duty:.3f} sensores ligados. Tres fixos, rodizio e sorteio tiveram falhas. Este seletor ainda aciona os nove por intervalos curtos; nao e uma estrategia que nunca os ativa simultaneamente.

Essa conclusao e restrita a replicas favoraveis de bias e ao supervisor definido abaixo. Nao demonstra economia real de energia, vantagem de area ou uma arquitetura completa 9x9. A selecao de sensores foi simulada em Python; suas estimativas causais alimentaram a dinamica da porta no LTspice. O supervisor nao esta implementado com componentes analogicos no deck.

## Metodo e fronteira do controlador

Porta MLC AND anterior com dois pilares de correcao, amortecimento e bias. Perfil assimetrico: amortecimento +/-0,15% a 500 Hz; bias +/-0,010 a 137 Hz, fase 40 graus. O pilar A conserva a replica anterior. Apenas a medicao do pilar B e selecionada. Ambos compartilham capacidade nominal de 100 uA. A latencia posterior de 50 us e o filtro de 100 us permanecem.

Medicoes a cada 100 us, tempo de despertar de 200 us. Sensores desativados ficam indisponiveis ao controlador. O simulador conhece os valores potenciais de todos para representar o ambiente, mas o seletor somente recebe os validos. O seletor nao recebe identidades de falha, a resposta AND correta, x ou y. A leitura fica constante ate a proxima amostra; se nenhum sensor estiver valido, conserva a ultima estimativa. Com sensores parcialmente acordados, usa a mediana dos validos (a mediana de um numero par usa a media dos centrais). Nao exigimos quorum minimo de tres durante o despertar; isso e um limite desta implementacao.

Sensor i mede a perturbacao de bias com offset compartilhado -0,0002, offset individual (i-4)*0,00002 para i=0..8, e ruido determinista senoidal com frequencia 311+47*i Hz e fase 0,53*i rad. Amplitude 0,00005, ou 0,0007 no perfil ruido_alto. Sao fontes deterministas distintas; nao e ruido aleatorio branco nem independencia estatistica provada. As replicas saudaveis acompanham diretamente o desvio, separando-o das entradas logicas, ainda uma hipotese favoravel.

Deslocamentos fixos durante dois intervalos de falha: 163,35 a 363,35 ms (+0,020) e 463,35 a 683,35 ms (-0,020), unidades normalizadas. Uma falha afeta o sensor 0, depois o 7. Quatro falhas afetam [0,1,2,3], depois [2,5,7,8]. Erro comum afeta todos os nove. As falhas surgem entre amostras e mudam de posicao. Fora desses intervalos os sensores recuperam suas leituras saudaveis.

Cada deck tem x inicial=-0,37/+0,37, y=-0,2, e as 17 entradas de 50 ms que cobrem as 16 transicoes, sem reiniciar a porta. Acerto exige x negativo em 00/01/10 e positivo em 11 durante toda a janela de 30 a 49 ms de cada bloco, usando extremos numericos. Contagens deterministas nao sao probabilidades de hardware.

## Politicas previamente definidas

- **Nove fixos:** todos solicitados continuamente; mediana dos validos.
- **Tres fixos:** indices 0,1,2 continuamente.
- **Rodizio:** grupos [0,1,2], [3,4,5], [6,7,8], mudando a cada 5 ms.
- **Sorteio:** tres sensores sem reposicao, novo grupo a cada 5 ms, sementes 19,73,211. As tres realizacoes sao mostradas; nao selecionamos apenas a melhor.
- **Adaptativo:** inicializa todos por 600 us; normalmente tres selecionados pela proximidade da mediana da ultima verificacao completa. A cada 5 ms, solicita todos por 600 us. Divergencia max-min acima de 0,001 por duas amostras solicita uma verificacao de pelo menos 2 ms. Com nove validos, seleciona tres sensores com residual ate 0,0005 e menor distancia da mediana. Se nao houver tres, conserva a selecao anterior. Trocas so entram no proximo tick, sem usar amostras futuras.

O tempo minimo de verificacao e a exigencia de duas amostras amortecem trocas por um unico desvio. Este prototipo passa diretamente de tres para nove, sem um estado intermediario de cinco. Os limiares e os horarios foram definidos no preparador antes de executar os decks; nao foram otimizados pelos acertos das janelas. O supervisor e uma simulacao discreta ideal, sem tempo de processamento, falha propria ou consumo definido.

## Resultados por perfil

Cada numero tem 34 janelas. No sorteio, a celula traz as contagens das sementes 19,73,211, cada uma com 34 janelas.

| Perfil | Nove fixos | Tres fixos | Rodizio | Sorteio (3 sementes) | Adaptativo |
|---|---|---|---|---|---|
'''+ '\n'.join(table)+'''

## Conjunto principal

O sorteio tem tres vezes mais trajetorias por causa das tres sementes. As contagens devem ser lidas com seus denominadores; nao sao uma estimativa estatistica de confiabilidade. A media de ligados inclui sensores acordando, nao apenas os validos, e cada deck tem a mesma duracao.

| Politica | Janelas corretas | Trajetorias inteiras corretas | Media de sensores ligados | Menor margem |
|---|---|---|---|---|
'''+ '\n'.join(aggregate)+f'''

No perfil de quatro falhas, a reducao de quantidade media solicitada pelo adaptativo frente a nove fixos foi {saving:.2f}%. Esse numero descreve uso de sensores no modelo, nao energia economizada. Quantidade de trocas, tempo de despertar, combinacao das leituras e processamento tambem tem custo.

## Deteccao e uso do adaptativo

No perfil de quatro falhas, os primeiros alarmes de divergencia vieram {latencies[0]} e {latencies[1]} ms depois de cada inicio de falha. Um alarme identifica discordancia, nao prova qual sensor esta errado. O calculo de latencia usa as falhas conhecidas somente na analise posterior, nunca como entrada do controlador. Falhas em sensores desligados podem nao gerar alarme ate a verificacao seguinte; erro comum concordante pode nunca gerar alarme.

| Perfil | Media de ligados | Alarme no tempo sem falha injetada | Trocas individuais ligar/desligar |
|---|---|---|---|
'''+ '\n'.join(usage)+'''

Com ruido alto, o supervisor ativa mais sensores e acusa muitas divergencias mesmo sem falhas injetadas. Isso reduz o ganho de uso e mostra que os limiares precisam ser avaliados com distribuicoes de ruido e sensores reais. O modelo atual nao estima energia dessas trocas.

## Refinamento de tempo

Os oito decks de nove fixos e adaptativo em saudaveis, quatro falhas, erro comum e ruido alto foram repetidos com passo maximo de 2,5 us. O supervisor manteve dt=100 us e os mesmos comandos; este ensaio refina a solucao da porta, nao a amostragem do supervisor.

| Perfil | Politica | Acertos 5 us | Acertos 2,5 us | Menor margem 2,5 us |
|---|---|---|---|---|
'''+ '\n'.join(ref_table)+f'''

Houve {len(changes)} janelas com classificacao alterada nos pares refinados. As contagens, quando iguais, nao implicam curvas identicas. O passo do supervisor, o tempo de despertar e os limiares nao foram varridos; a deteccao favoravel ainda precisa de outros horarios de falha e casos nao usados nesta comparacao.

Tolerancias do LTspice: reltol=1e-6, vntol=1e-9, abstol=1e-12. Pico maximo registrado: {peak:.9f} uA, com capacidade nominal 100 uA; o analisador permite ate 0,005 uA de ultrapassagem numerica e preserva o valor medido.

## Escolha e limites

Para estes cenarios, usar selecao adaptativa quando a quantidade de participantes importa e verificacoes completas curtas sao permitidas. Nove fixos tem uma regra mais simples e evita a dependencia do escalonamento, mas usa nove continuamente. Tres fixos bastaram no cenario saudavel e de uma falha; rodizio e sorteio nao substituem a protecao da maioria saudavel sob quatro falhas. O adaptativo nao resolve erro comum; e preciso uma referencia com outro mecanismo ou diagnostico independente.

A comparacao e de um seletor definido, nao de todos os algoritmos possiveis. Nao inferimos um melhor universal. Nao testamos sensores com estados internos ao desligar, falhas do supervisor, corrente real de alimentacao, temperatura fisica ou as nove portas interligadas. Nao reestimamos Lyapunov para todas as condicoes. A funcao de cada canal e investigada separadamente na etapa 10; a uniao do seletor adaptativo com tres pilares ainda nao foi ensaiada.

## Arquivos e visualizacao no LTspice

43 decks (35 principais, 8 refinados), 86 trajetorias, 1462 janelas. Os arquivos *_sinais.inc sao as estimativas e monitores PWL do supervisor; *_supervisor.json registra uso, alarmes e parametros. Modelos, casos, logs e RAW tornam cada execucao reproduzivel.

Para comparar quatro falhas, abrir SEL_p2_adaptativo_s19.cir e SEL_p2_nove_fixos_s19.cir, mantendo os includes na mesma pasta. Em cada arquivo, usar Select Steps para uma condicao inicial por vez. Adicionar V(saida), V(referencia) e V(ler) para os acertos; V(ativos) em outro painel mostra tres ou nove no adaptativo e nove no fixo. V(validos) mostra a quantidade pronta depois de acordar. V(estimativa_b) e a leitura usada, nao a resposta logica.

Preparacao: preparar_selecao.py, preparar_refinamento.py. Execucao: executar_lote.ps1, com manifestos dos casos. Analise: analisar_selecao.py e gerar_relatorio.py. Os resultados completos estao em resultados_selecao.csv, resumo_selecao.json e comparacao_refinamento.json.
'''
(ROOT/'ETAPA9_RESULTADOS.md').write_text(report,encoding='utf-8')
print('Relatorio de selecao salvo; classificacoes alteradas:',len(changes))
