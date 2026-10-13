from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
S=json.loads((ROOT/'resumo.json').read_text())
R=list(csv.DictReader((ROOT/'resultados.csv').open(encoding='utf-8-sig')))
LABELS=['Comum proporcional','Dois grupos 50/50','Dois grupos com emprestimo','Prioridade B,D,A,C','Comum com reserva local']
PN=['Equilibrado','AB exige mais','CD exige mais','Todos exigem']
M=[s for s in S if s['arquivo'].startswith('COORD_perfil')]
MR=[r for r in R if r['arquivo'].startswith('COORD_perfil')]
if len(M)!=40:raise ValueError('Faltam grupos principais')
robust={p:0 for p in range(5)};changes=[]
for p in range(5):
    for prof in range(4):
        for x in ['-0.37','0.37']:
            for win in range(17):
                rows=[r for r in MR if int(r['politica_coord'])==p and int(r['perfil'])==prof and r['x_inicial']==x and int(r['janela'])==win]
                if len(rows)!=2:raise ValueError('Pareamento incompleto')
                robust[p]+=int(all(r['acerto']=='1' for r in rows))
                if rows[0]['acerto']!=rows[1]['acerto']:changes.append({'perfil':prof,'politica':p,'x_inicial':x,'janela':win,'classificacoes':[{k:r[k] for k in ['passo','acerto','margem']} for r in rows]})
(ROOT/'comparacao_passos.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
aggregate=[]
for p in range(5):
    a=[s for s in M if s['politica_coord']==p]
    aggregate.append(f"| {LABELS[p]} | {sum(v['corretas'] for v in a)}/272 | {sum(v['trajetorias_corretas'] for v in a)}/16 | {robust[p]}/136 |")
profiles=[]
for prof in range(4):
    cells=[f"{sum(v['corretas'] for v in M if v['perfil']==prof and v['politica_coord']==p)}/68" for p in range(5)]
    profiles.append('| '+PN[prof]+' | '+' | '.join(cells)+' |')
faults=[]
for f,name in [(0,'Sem falha'),(1,'Parou e perdeu heartbeat'),(2,'Atraso permanente 500 us'),(3,'Inverteu o sinal'),(4,'Parou, heartbeat permaneceu')]:
    cells=[]
    for p in range(5):
        candidates=[v for v in S if v['perfil']==1 and v['politica_coord']==p and v['falha_coord']==f and v['passo']==2.5e-6 and (v['arquivo'].startswith('COORD_perfil') if f==0 else v['arquivo'] in ['COORD_falha1','COORD_falha2','COORD_falha3','COORD_falha4_AB'])]
        if len(candidates)!=1:raise ValueError(f'Grupo de falha incompleto {f},{p}')
        cells.append(f"{candidates[0]['corretas']}/34")
    faults.append('| '+name+' | '+' | '.join(cells)+' |')
diag=[]
for p in range(5):
    a=[v for v in S if v['politica_coord']==p]
    diag.append(f"| {LABELS[p]} | {max(v['pico_sem_protecao_max'] for v in a)*1e6:.4f} | {max(v['sobra_max'] for v in a)*1e6:.4f} | {max(v['uso_protecao_max'] for v in a)*100:.3f}% | {max(v['uso_reserva_max'] for v in a)*100:.3f}% |")
reserve=[]
for f in range(1,5):
    a=next(v for v in S if v['perfil']==1 and v['politica_coord']==4 and v['falha_coord']==f and v['arquivo'] in ['COORD_falha1','COORD_falha2','COORD_falha3','COORD_falha4_AB'])
    reserve.append(f"| {f} | {a['uso_reserva_max']*100:.4f}% | {a['corretas']}/34 |")
peak=max(s['pico_orcamento_uA'] for s in S)
over=sum(s['trajetorias_fora_tolerancia'] for s in S if s['arquivo']!='COORD_precisao')
precision=[]
for p in [0,2,4]:
    original=next(r for r in R if r['arquivo']=='COORD_falha4_AB' and int(r['politica_coord'])==p and r['x_inicial']=='-0.37')
    refined=next(v for v in S if v['arquivo']=='COORD_precisao' and v['politica_coord']==p)
    precision.append(f"| {LABELS[p]} | {float(original['pico_orcamento_uA']):.9f} | {refined['pico_orcamento_uA']:.9f} | {refined['corretas']}/17 | {refined['trajetorias_fora_tolerancia']} |")
text=f'''# Etapa 12: um coordenador, dois grupos e alternativas

Atualizacao de 12/10/2026: a conferencia independente em [MEDICAO_CORRENTE.md](MEDICAO_CORRENTE.md) mostrou que o pequeno excesso de V(orcamento) nao foi confirmado pela soma das correntes aplicadas nos oito ensaios repetidos. As 45 falhas historicas abaixo se referem ao criterio baseado nesse monitor; nao demonstram, sozinhas, excesso de corrente aplicada. Os outros casos antigos ainda nao foram conferidos por esse metodo. A alternativa que soma A/B/C antes de alocar esta documentada na etapa 13.

Comparacao de cinco regras de alocacao e protecao para A/B/C/D, mantendo capacidade nominal total de 100 uA. O pilar D definido na etapa 11 corrige deriva multiplicativa da curva nao linear g(x) no estado x; os outros atuam em y. As contagens abaixo incluem falhas e sensibilidade numerica, sem presumir que mais camadas ou dois coordenadores sejam melhores.

Os sensores sao replicas continuas favoraveis do modelo. Esta etapa isola a coordenacao de corrente; ainda nao implementa os nove subpilares adaptativos em cada um dos quatro pilares nem calcula o consumo de uma piramide fisica.

## Cinco alternativas

| Regra | Alocacao | Consequencia estrutural |
|---|---|---|
| Comum proporcional | Reduz todas as demandas na mesma proporcao quando a soma excede 100 uA | Compartilha recursos, mas uma falha do topo pode afetar todos os canais |
| Dois grupos 50/50 | AB recebe 50 uA; CD recebe 50 uA; reparticao proporcional dentro de cada grupo | Pode faltar corrente num grupo enquanto sobra no outro; falha em um grupo afeta seus dois canais |
| Dois grupos com emprestimo | Cada grupo recebe sua metade mais capacidade ociosa relatada pelo outro, com atraso de 50 us | Reduz capacidade presa, mas informacao antiga pode conceder demais; usa protecao comum final |
| Prioridade B,D,A,C | Atende B, depois D, depois A e C com a capacidade que resta | Pode proteger alguns desvios e deixar outros sem recursos; prioridade fixa e uma hipotese deste ensaio |
| Comum com reserva local | Normalmente comum proporcional; com detector de falha, cada pilar usa sua demanda atual ate 25 uA | Reserva evita depender das ordens do topo, mas sua divisao fixa pode ser insuficiente e o detector pode falhar |

Todos usam uma protecao final independente no modelo: rejeitar um comando de sinal oposto ao pedido filtrado atual e reduzir a soma restante se exceder 100 uA. Essa protecao conhece os pedidos dos pilares, nao a resposta AND esperada. Ela e ideal e compartilhada; sua propria falha nao foi injetada. Dois coordenadores neste ensaio nao eliminam todos os elementos comuns. Essa protecao altera tambem o efeito de ordens atrasadas, portanto o teste de atraso avalia o conjunto protegido.

O emprestimo concede quota1=50+max(0,50-pedido2_atrasado) e quota2=50+max(0,50-pedido1_atrasado), em uA. Quando ambos passam a pedir mais antes de receber a informacao nova, a soma concedida pode superar 100. Os picos antes da protecao sao preservados e nao contam como corrente realmente aplicada.

## Sensores, tempos e referencia

Equacoes MLC anteriores, com curva nominal interna -1,02/externa -0,55, escala 100 us, bias -0,005, entradas +/-0,005 e excitacao 0,11*sin(0,74*time/escala). Sensores com latencia de 50 us, filtro de 100 us e erros anteriores: A multiplicativo +0,0002, B aditivo -0,0002, C +0,0002 e D +0,00002. A replica mede a deriva resistiva; B/C/D acompanham diretamente o respectivo parametro. Essa relacao favoravel ainda exige circuito de medicao e verificacao fisica.

Fonte conceitual das equacoes: [Murali et al.](https://arxiv.org/pdf/1811.10029). As derivas, sensores, regras, falhas e protecoes deste estudo sao modelos novos aqui, nao resultados atribuidos ao artigo. A implementacao usa fontes comportamentais de corrente, recurso documentado pela [Analog Devices](https://www.analog.com/en/resources/technical-articles/ltspice-modeling-constant-power-loads.html).

O detector de reserva observa heartbeat: pulsos de 100 us a cada 200 us, bordas de 0,1 us. Sua memoria usa capacitor de 1 nF, carga por 10 kohm (constante de 10 us) e descarga por 500 kohm (0,5 ms). Saude abaixo de 0,3 solicita reserva. Outro detector observa comandos com sinal oposto ao pedido e acumula alerta com os mesmos tempos; alerta acima de 0,3 tambem solicita reserva. Os tempos reais ate esses limiares dependem do estado anterior; nao alegamos deteccao exata de 10 us.

O detector nao recebe o parametro de falha. Os parametros somente representam a injecao fisica no comando e no heartbeat. Se o topo parar de corrigir mas mantiver heartbeat e comandos zero, o produto comando*pedido nao fica negativo: este detector nao percebe essa falha. Mesmo detectando, 25 uA por canal nao garante a correcao que uma reparticao dinamica permitiria.

## Quatro perfis principais

Amplitude A/D e relativa; B/C em unidades normalizadas. Frequencias: A 500 Hz, B 137 Hz/fase 40 graus, C 73 Hz/fase 65 e D 211 Hz/fase 17.

| Perfil | A | B | C | D |
|---|---|---|---|---|
| Equilibrado | 0,0025 | 0,003 | 0,002 | 0,004 |
| AB exige mais | 0,0015 | 0,010 | 0,001 | 0,001 |
| CD exige mais | 0,0005 | 0,001 | 0,005 | 0,008 |
| Todos exigem | 0,006 | 0,009 | 0,007 | 0,008 |

Cada regra e perfil teve x inicial=-0,37/+0,37, y=-0,2 e passos maximos de 2,5 e 1,25 us: quatro trajetorias e 68 janelas por celula. Sequencia de 17 blocos de 50 ms, todas as 16 transicoes entre 00/01/10/11 sem reiniciar o estado. Acomodacao de 30 ms; extremos de x de 30 a 49 ms. Para AND, 11 exige x>0; os demais x<0. Um pulso errado dentro da janela conta como falha, mesmo se a media estiver correta.

| Perfil | Comum | Dois 50/50 | Emprestimo | Prioridade | Reserva local |
|---|---|---|---|---|---|
'''+ '\n'.join(profiles)+'''

## Conjunto principal e refinamento

O ultimo indicador exige que a mesma janela da mesma condicao inicial passe nos dois passos de tempo. Ele nao e uma prova de convergencia continua; evita selecionar apenas a execucao mais favoravel.

| Regra | Janelas corretas nos dois ensaios somados | Trajetorias inteiras corretas | Janelas corretas em ambos os passos |
|---|---|---|---|
'''+ '\n'.join(aggregate)+f'''

Houve {len(changes)} classificacoes alteradas entre os passos no conjunto principal. Os pares estao em comparacao_passos.json. Especialmente sob demanda alta, uma contagem maior num unico passo nao garante funcionamento confiavel. Nao reestimamos Lyapunov para todas estas perturbacoes; aparencia oscilante nao prova caos em cada caso.

## Falhas de coordenacao

Ensaios de falha no perfil AB exige mais, x inicial=-0,37/+0,37, passo 2,5 us. A janela de falhas 1,3,4 e de 343,35 a 403,35 ms: abrange o fim da leitura de 11 e a leitura de 01, exigindo resposta 1 e depois 0. Falha 2 e um atraso permanente de 500 us nas ordens dos coordenadores, nao um evento temporario.

1. Coordenador para, comandos zero e heartbeat ausente.
2. Ordens atrasadas 500 us em todos os canais, inclusive nos dois grupos.
3. Comandos do coordenador com sinal invertido; heartbeat continua.
4. Comandos zero enquanto heartbeat continua.

Nas regras comuns e prioridade, as falhas 1,3,4 afetam o topo inteiro. Nas duas regras por grupos, afetam somente o coordenador AB; CD continua. Isso representa o dominio de impacto dessas arquiteturas, nao uma falha identica no mesmo numero de canais. Nenhum grupo CD substitui automaticamente as funcoes que faltam em AB.

| Condicao | Comum | Dois 50/50 | Emprestimo | Prioridade | Reserva local |
|---|---|---|---|---|---|
'''+ '\n'.join(faults)+'''

O perfil equilibrado tambem foi testado para a falha 4, antes da extensao mais exigente de AB: todas as regras passaram em 34/34 e a reserva nao entrou. A porta acertar nessas condicoes nao demonstra que o detector identificou a falha. As derivas menores podem dispensar correcao por algum tempo; esse teste motivou medir o mesmo defeito no perfil AB, que exige mais atuacao.

## Pedidos, capacidade presa e protecao

Sobra aqui e min(capacidade nao aplicada, demanda nao atendida), medidos simultaneamente. E corrente que poderia estar disponivel quando existe um pedido nao servido, nao somente tempo ocioso normal. Os valores abaixo sao os maximos entre os casos de cada regra. Os percentuais sao os maiores usos medios de uma trajetoria, nao uma media global.

| Regra | Pico pedido antes da protecao (uA) | Pico de sobra com demanda nao atendida (uA) | Uso de protecao maximo | Uso de reserva maximo |
|---|---|---|---|---|
'''+ '\n'.join(diag)+'''

A divisao fixa pode limitar AB mesmo quando o pedido total cabe em 100 uA. O emprestimo corrige parte desse problema, mas tem comunicacao e protecao adicionais. Uma camada superior que limita a soma continua sendo um componente comum. Priorizacao pode usar toda a capacidade e ainda negar a correcao de um canal importante. Um monitor de heartbeat atesta atividade, nao a exatidao da alocacao.

## Reserva nas falhas de AB

| Tipo de falha | Maior fracao da trajetoria com reserva | Janelas corretas da reserva |
|---|---|---|
'''+ '\n'.join(reserve)+f'''

A reserva pode identificar silencio e sinal oposto, mas nao o silencio com heartbeat presente. Um diagnostico posterior deveria confrontar pedido e corrente realmente aplicada por tempo suficiente, contando saturacao legitima e recurso disponivel. Essa melhoria nao foi implementada nesta comparacao. Corrigir o detector sem rever as quotas de 25 uA tambem nao garante que a reserva tenha capacidade suficiente.

## Precisao, protecao e escopo

Pico indicado pelo monitor V(orcamento): {peak:.9f} uA para capacidade nominal 100 uA. A tolerancia de verificacao numerica permaneceu 0,005 uA; {over} trajetorias originais ultrapassaram esse criterio e foram marcadas como falha do criterio baseado no monitor, sem esconder os picos. As contagens de acerto logico sao uma metrica separada. Nao alegamos que todos os casos passaram no limite de corrente. Reltol=1e-6, vntol=1e-9, abstol=1e-12, solver normal/trap, threads=1. Threads limita apenas o processamento dos ensaios, documentado pelo [suporte da Analog Devices](https://ez.analog.com/design-tools-and-calculators/ltspice/f/q-a/592257/option-to-limit-the-maximum-number-of-threads/577366); nao aumenta capacidade de corrente.

As demandas de corrente sao representadas numericamente por tensoes pequenas, da ordem de 0,0001 V. A tolerancia absoluta de tensao pode afetar sua precisao. Repetimos tres casos com vntol=1e-11, sem trocar seus parametros fisicos ou passo, e preservamos o ensaio original:

| Regra, mesmo x inicial=-0,37 | Pico original (uA) | Pico refinado (uA) | Acertos refinados | Trajetorias refinadas fora da tolerancia |
|---|---|---|---|---|
'''+ '\n'.join(precision)+f'''

O refinamento selecionado investiga o problema de resolucao e nao substitui a validacao de capacidade em todos os casos. Para uma realizacao, escalar os sinais internos e validar um limitador de corrente com componentes reais. Mesmo um limite matematico ideal pode produzir residuos numericos no simulador.

130 trajetorias na comparacao principal, 2210 janelas: 80 principais, 40 de falhas no perfil AB e 10 de falha com heartbeat mantido no equilibrado. Tres repeticoes adicionais de precisao acrescentam 51 janelas, analisadas separadamente. Ensaios iniciais incompletos com detector mais rapido e coleta sem alguns sinais auxiliares foram preservados em pastas preliminar_* e excluidos das contagens. Todos os resultados finais usam o detector de carga 10 us, descarga 0,5 ms e sinais auxiliares salvos. O perfil AB das falhas foi escolhido apos inspecao inicial do equilibrado e antes de executar suas falhas; nao e um conjunto cego independente de selecao da arquitetura.

Nao testamos erro compartilhado das replicas, falha da protecao final, falha do detector, custos reais, limitacoes de alimentacao, varios ordenamentos de prioridade ou outros agrupamentos como AC/BD. Os comandos dependem de sensores continuos, nao de 36 sensores adaptativos. Igualar capacidade de atuacao nao iguala consumo, area ou custo. A proxima integracao deve reunir os seletores de subpilares e comparar casos novos com custo e atraso do supervisor.

## Evidencias

Modelos MLC_coordenadores.inc e MLC_coordenadores_falhas.inc, nove decks de comparacao, manifestos, logs e RAW. resultados.csv, resumo.json e comparacao_passos.json sao a evidencia final. parcial_RAW.json e somente acompanhamento aproximado das curvas durante o processamento; nao e a fonte das contagens finais, que usam .meas concluido e verificacao de todos os blocos.

Preparacao: preparar_coordenadores.py e as funcoes de etapa11/preparar_d.py. Executar os lotes e as duas extensoes de falha silenciosa com executar.ps1. Analise: etapa11/analisar.py com todos os nove nomes, depois gerar_relatorio.py. A demonstracao de D e o relatorio da etapa 11 ficam na pasta anterior.
'''
(ROOT/'ETAPA12_RESULTADOS.md').write_text(text,encoding='utf-8')
print('Relatorio de coordenadores salvo; classificacoes alteradas:',len(changes))
