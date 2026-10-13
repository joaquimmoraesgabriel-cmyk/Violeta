# Etapa 10: funcao dos pilares de correcao

Definimos e testamos tres canais que corrigem termos diferentes das equacoes MLC. O terceiro melhorou os resultados comparados com A+B no cenario de excitacao forte em cada passo testado; contudo a classificacao variou com o passo de tempo e houve falha em 0,625 us. Portanto nao demonstramos confiabilidade total ou convergencia quantitativa nesse cenario. A utilidade do canal C permanece condicionada ao modelo e ao ensaio, sem justificar preencher nove funcoes.

## Funcao, medicao e atuacao

| Pilar | Desvio que trata | Medicao no modelo | Como atua |
|---|---|---|---|
| A: amortecimento | Mudanca da perda de energia associada ao termo que multiplica y | Replica resistiva com erro multiplicativo +0,0002; estimativa 1/V(sensor_a)-2 | Compensa o termo alterado com corrente proporcional a estimativa de desvio e ao estado y |
| B: bias | Deslocamento aditivo do termo de bias, que pode deslocar a dinamica entre regioes | Replica ideal do desvio de bias, offset -0,0002 | Aplica corrente de sinal oposto ao desvio estimado |
| C: excitacao | Mudanca da amplitude da excitacao senoidal externa | Replica ideal da amplitude desviada, offset +0,0002; fase da excitacao conhecida | Aplica corrente oposta ao desvio de amplitude multiplicado pela senoide de referencia |

Cada estimativa tem latencia de 50 us e filtro de primeira ordem de 100 us. As correntes sao demandas assinadas; o coordenador escala todas na mesma proporcao se a soma dos modulos ultrapassar a capacidade nominal de 100 uA. Retirar um pilar zera sua demanda antes da reparticao: a capacidade nao fica artificialmente reservada para canais desligados.

Os sinais positivos e negativos da ideia original podem ser representados por estas correntes em sentidos opostos. Nao sao passos obrigatorios de +/-1 V. A escala de 100 us e os capacitores de 1 uF convertem as equacoes em correntes; a corrente de cada canal ainda e de uma fonte comportamental ideal, sem alimentacao ou atuador fisico definido.

O canal C usa a fase conhecida da excitacao gerada pelo proprio modelo. Supomos ser possivel medir o desvio de amplitude separadamente. Essa replica e favoravel; medir amplitudes e fases reais, atraso de demodulacao e erro de referencia exige outro circuito. Nao transformamos diretamente temperatura em um quarto canal: ela pode alterar varios destes parametros, e seria preciso conhecer suas relacoes fisicas.

## Perturbacoes e comparacao causal por retirada

Amortecimento +/-0,5% a 500 Hz; bias +/-0,006 a 137 Hz, fase 40 graus, como o perfil equilibrado da etapa 7. Acrescentamos desvio de amplitude de excitacao a 73 Hz, fase 65 graus: +/-0,004 (menor) ou +/-0,012 (forte), unidades normalizadas, sobre amplitude nominal 0,11. Nao e desvio percentual nem uma tensao fisica calibrada.

Testamos as oito combinacoes de canais, mesmos desvios e capacidade de atuacao. Cada celula tem 34 janelas: x inicial=-0,37/+0,37, y=-0,2, passo maximo=5 us. Replica B continua unica e continua, sem o supervisor adaptativo da etapa 9. As duas etapas estudam partes separadas da arquitetura; a combinacao ainda nao foi validada.

| Canais ligados | Acertos, desvio menor | Menor margem | Acertos, desvio forte | Menor margem |
|---|---|---|---|---|
| Nenhum | 21/34 | -1.374037 | 19/34 | -1.416850 |
| A | 26/34 | -1.360661 | 17/34 | -1.396110 |
| B | 30/34 | -0.227194 | 22/34 | -1.377015 |
| A+B | 34/34 | 0.095372 | 31/34 | -1.361814 |
| C | 18/34 | -1.404278 | 20/34 | -1.409827 |
| A+C | 22/34 | -1.355238 | 24/34 | -1.402234 |
| B+C | 31/34 | -0.027792 | 30/34 | -1.210217 |
| A+B+C | 34/34 | 0.228917 | 32/34 | -1.295268 |

A retirada de canais sob os mesmos desvios mostra que os canais nao sao substitutos perfeitos. No desvio menor, A+B+C passou em 34/34; retirar A deixou B+C em 31/34 e retirar B deixou A+C em 22/34. Retirar C manteve A+B em 34/34, mas reduziu a menor margem no passo de 5 us de aproximadamente 0,233 para 0,097. O terceiro canal nao foi necessario para acertar esse conjunto, mas melhorou a margem nesse passo.

No desvio forte e passo de 5 us, A+B+C ficou em 32/34; retirar A deixou B+C em 30/34, retirar B deixou A+C em 24/34, retirar C deixou A+B em 31/34. A hierarquia nao removeu todas as falhas. Corrigir C sozinho tambem nao tratou os outros desvios: 20/34 no cenario forte.

## Refinamento e limite da conclusao

O refinamento inicial em 2,5 us alterou contagens no cenario forte, motivando ensaios adicionais em 1,25 e 0,625 us. Nenhuma configuracao foi escolhida olhando apenas um passo que passou.

| Passo maximo (us) | A+B, acertos | Menor margem | A+B+C, acertos | Menor margem |
|---|---|---|---|---|
| 5 | 31/34 | -1.361814 | 32/34 | -1.295268 |
| 2.5 | 32/34 | -0.124638 | 34/34 | 0.069184 |
| 1.25 | 33/34 | -0.004150 | 34/34 | 0.039292 |
| 0.625 | 31/34 | -0.138338 | 33/34 | -0.115303 |

O canal C melhorou a contagem em todos estes passos, mas 34/34 em 2,5 e 1,25 us nao foi preservado em 0,625 us. A contagem A+B tambem nao convergiu monotonicamente. O ensaio forte continua numericamente sensivel e nao permite afirmar uma faixa de funcionamento totalmente confiavel. Nao devemos interpretar oscilar ou acertar uma trajetoria como prova de caos ou desempenho fisico. A dinamica nominal foi analisada anteriormente; nao reestimamos Lyapunov para estes perfis.

No desvio menor, A+B e A+B+C mantiveram 34/34 no refinamento de 2,5 us; a margem tambem favoreceu A+B+C, mas os valores mudaram. O resultado mais defensavel e a funcao definida de C e a melhora relativa observada, com a necessidade de novas verificacoes para o caso forte.

Tolerancias: reltol=1e-6, vntol=1e-9, abstol=1e-12. Pico maximo registrado 100.001088867 uA. Capacidade nominal 100 uA, tolerancia numerica explicita do analisador 0,005 uA; os picos sao preservados. Nao igualamos consumo total de sensores e controladores, area ou custo. Todos os canais usam replicas favoraveis; modelos de componentes, ruído real e circuitos de medicao ainda faltam.

## Como cada subpilar funciona

Os nove subpilares da etapa 9 sao nove medicoes redundantes do MESMO desvio de bias do pilar B, com erros individuais definidos. Nao ha nove atuadores diferentes corrigindo nove causas. O seletor usa normalmente tres, verifica os nove periodicamente e chama reforco com divergencia; a mediana selecionada passa pelo filtro e pelo atuador B. As posicoes podem ser trocadas; um subpilar nao e intrinsicamente 'o da temperatura' ou 'o da vibracao'.

Sensores de grandezas diferentes poderiam ter funcoes especializadas e gatilhos diferentes, mas nao seriam replicas para a mesma mediana. Para usar nove pilares de atuacao, primeiro identificar desvios adicionais independentes e uma medicao util para cada um. Para este estudo, A, B e C sao as funcoes que modelamos e comparamos. O numero nove nao determina quantos canais precisam existir.

## Desenho de arquitetura candidata

Sensores/estimativas -> validacao e selecao -> filtro de cada pilar -> demanda de correcao -> coordenador de capacidade -> correntes no estado y da porta -> leitura de x para 0/1.

No ensaio de selecao, a parte B tem nove replicas e supervisor adaptativo, com A ligado e sem C. No ensaio de pilares, A/B/C sao comparados com sensores continuos. Juntar o seletor adaptativo a A/B/C e testar o custo e a dinamica conjuntos e uma proxima etapa; nao contamos a uniao como validada por estes resultados separados.

## Ver no LTspice

Abrir MLC_pilares_demo.cir com MLC_tres_pilares.inc na mesma pasta. Dois passos: A+B e A+B+C, desvio menor, x inicial=+0,37. Adicionar V(saida), V(referencia) e V(ler) e escolher um passo por vez. Ambos passam. Para ver a diferenca de margem, adicionar V(x) em outro painel e observar sua distancia de zero durante a leitura. Para ver o trabalho dos canais, adicionar I(Bcorrecao_a), I(Bcorrecao_b), I(Bcorrecao_c); o terceiro e zero em A+B.

## Evidencias

50 trajetorias, 850 janelas: 32 principais, 8 de refinamento inicial, 8 motivadas pela sensibilidade numerica e 2 de demonstracao. O modelo, quatro decks, manifestos JSON, logs e RAW estao nesta pasta. resultados_pilares.csv e resumo_pilares.json preservam medidas, margens e classificacoes. Preparadores e analisar_pilares.py permitem reproduzir o ensaio.

Os limiares e a leitura AND permanecem os anteriores: 30 ms de acomodacao e 19 ms de leitura por bloco de 50 ms, cobrindo as 16 transicoes entre entradas. As contagens sao deterministas e dependem desse criterio temporal. Nao medimos vantagem sobre logica digital convencional, nem funcionamento fisico de uma rede completa.
