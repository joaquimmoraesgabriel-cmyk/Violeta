# Etapa 4: separar atraso, tempo de resposta e corrente

Nas condicoes testadas, aumentar apenas a latencia de 50 para 500 us produziu a maior perda de acertos: 35/68 janelas, contra 68/68 na configuracao de base. Reduzir apenas a corrente maxima de 100 para 20 uA manteve 68/68. Tornar apenas a resposta mais lenta, de 100 us para 1 ms, resultou em 63/68.

Isso sustenta priorizar a velocidade de reacao neste modelo. Ainda nao estabelece um atraso maximo suportado, nem prova que a corrente reduzida funciona em outras perturbacoes ou numa montagem fisica.

## Abrir a demonstracao

Abra **MLC_fatores_demo.cir** no LTspice com o filtro All Files e clique em Run. Mantenha MLC_fatores.inc na mesma pasta.

Adicione V(x) e V(saida) ao grafico. Para acompanhar as correcoes, adicione V(perturbacao), V(ajuste) e I(Bcorrecao), em paineis separados se necessario. Use Step Legend ou Select Steps para comparar apenas duas execucoes por vez.

| Passo | Grupo | Alteracao em relacao a base | Janelas corretas na demonstracao |
|---|---:|---|---:|
| 1 | 0 | Base | 17/17 |
| 2 | 1 | Apenas maior atraso | 9/17 |
| 3 | 2 | Apenas resposta mais lenta | 14/17 |
| 4 | 4 | Apenas menor corrente maxima | 17/17 |
| 5 | 7 | As tres alteracoes juntas | 8/17 |

O grafico comparacao_fatores.svg mostra o resultado do ensaio completo, com quatro trajetorias por configuracao.

## Diferenca entre os fatores

- **Latencia:** tempo que a informacao medida leva ate chegar ao filtro do pilar. Testamos 50 e 500 us.
- **Tempo de resposta:** constante de tempo do filtro RC; descreve a velocidade com que o ajuste acompanha uma mudanca depois da latencia. Testamos 100 us e 1 ms.
- **Limite de corrente:** maior intensidade positiva ou negativa de correcao que o atuador permite. Testamos +/-100 e +/-20 uA.

O filtro e uma resposta de primeira ordem: a constante de tempo nao e o tempo para completar toda a correcao. Latencia e tempo de resposta sao duas limitacoes diferentes e foram variados separadamente.

Os valores de corrente e tempo pertencem ao modelo comportamental escalado; ainda nao sao especificacoes de um controlador fisico pronto.

## Metodo

Executamos as oito combinacoes de dois valores de cada um dos tres fatores. Isso permite comparar configuracoes que diferem em um unico fator e observar como os fatores interagem. Os casos foram definidos antes das simulacoes; a porta, as entradas e o criterio de leitura permaneceram fixos.

Usamos a perturbacao rapida que expôs as falhas na etapa anterior: uma senoide de 500 Hz que altera o amortecimento em +/-0,5%. A replica acompanha essa perturbacao com erro multiplicativo de +0,02%. O controlador usa a replica e o estado y, sem receber a resposta AND desejada.

Para cada configuracao, executamos x inicial=-0,37 e +0,37, y inicial=-0,2, e passos maximos de 5 e 2,5 us. Sao quatro trajetorias por configuracao, 32 no ensaio completo. Cada uma tem 17 blocos de entrada que cobrem todas as 16 transicoes possiveis entre os pares 00, 01, 10 e 11, sem reiniciar o estado entre blocos.

Cada entrada dura 50 ms. Reservamos os primeiros 30 ms para acomodacao e avaliamos todo o intervalo de 30 a 49 ms. A janela so passa se x permanece no lado correto de zero nos extremos calculados pelo LTspice: negativo para 00/01/10 e positivo para 11. O limiar continua sendo zero; nao usamos uma leitura instantanea nem recalibramos a porta.

O ensaio tem 544 janelas; a demonstracao acrescenta cinco trajetorias e 85 janelas. Sao resultados deterministas, nao testes aleatorios independentes ou probabilidades de sucesso em hardware. A verificacao com dois passos numericos e limitada e nao prova o comportamento para todo instante continuo.

## Resultado completo

Cada configuracao abaixo tem 68 janelas, de quatro trajetorias.

| Grupo | Latencia (us) | Resposta (us) | Limite (+/-uA) | Janelas corretas | Trajetorias inteiras corretas |
|---|---:|---:|---:|---:|---:|
| 0 | 50 | 100 | 100 | 68/68 | 4/4 |
| 1 | 500 | 100 | 100 | 35/68 | 0/4 |
| 2 | 50 | 1000 | 100 | 63/68 | 2/4 |
| 3 | 500 | 1000 | 100 | 47/68 | 0/4 |
| 4 | 50 | 100 | 20 | 68/68 | 4/4 |
| 5 | 500 | 100 | 20 | 43/68 | 0/4 |
| 6 | 50 | 1000 | 20 | 61/68 | 0/4 |
| 7 | 500 | 1000 | 20 | 40/68 | 0/4 |

Os fatores interagem. Por exemplo, reduzir a corrente com latencia de 500 us e resposta de 100 us aumentou a contagem de 35 para 43 acertos, mas ainda deixou falhas em todas as trajetorias. Portanto, maior capacidade de corrente nao garante melhor comportamento quando a correcao chega atrasada. Essa observacao e especifica dos casos avaliados; nao define uma regra universal.

## A limitacao de corrente atuou?

Na configuracao de base, o pico foi aproximadamente 71,87 uA, abaixo do limite de 100 uA. Ao reduzir apenas o limite para 20 uA, o atuador atingiu esse limite e ficou saturado por aproximadamente 62,35% do tempo nas janelas avaliadas. Mesmo assim, acertou todas elas. O menor afastamento de x de zero caiu de aproximadamente 0,22309 para 0,21470 e permaneceu positivo.

Assim, testamos um caso em que a saturacao realmente acontece e a leitura ainda funciona. Isso nao prova que 20 uA seja a menor corrente suficiente e nao demonstra economia de energia: nao medimos o consumo completo do circuito.

Na configuracao com apenas maior atraso, o pico foi aproximadamente 69,65 uA e nao houve saturacao. Suas falhas ocorreram mesmo com corrente disponivel. Isso reforca que o atraso pode prejudicar a operacao independentemente do limite de corrente neste modelo.

## Decisao para continuar

Mantemos latencia de 50 us e resposta de 100 us como configuracao de referencia. O limite de 20 uA e um candidato para os proximos ensaios, pois funcionou mesmo saturando neste conjunto. Precisamos verificar sua margem sob outras amplitudes, frequencias, sequencias e imprecisoes antes de adotá-lo como requisito.

O proximo ensaio pode testar valores intermediarios de latencia e novas frequencias, mantendo resposta e corrente fixas. Isso ajudara a delimitar uma faixa de funcionamento antes de ligar dois pilares entre si. Nenhum valor entre 50 e 500 us foi avaliado aqui; nao inferimos que o desempenho varie de forma monotona ou que exista um unico limite de atraso.

Ainda faltam ruido, temperatura fisica, erros independentes entre replica e parametro, deriva da referencia, atrasos variaveis, outros estados iniciais, portas interligadas e implementacao com componentes reais. Este ensaio separa fatores de um unico pilar; a estrutura completa de nove pilares e subpilares continua por definir e testar.

## Evidencias

- MLC_fatores_validacao.cir e MLC_fatores.inc: ensaio e modelo.
- casos_etapa4.json e grupos_etapa4.json: especificacoes anteriores a execucao.
- resultados_etapa4.csv: medidas e classificacao de cada janela.
- resumo_etapa4.json: contagens, margens, corrente, saturacao e lista de falhas.
- Arquivos .log e .raw: resultados preservados do LTspice 26.1.1.
- comparacao_fatores.svg: grafico feito com as contagens reais.
