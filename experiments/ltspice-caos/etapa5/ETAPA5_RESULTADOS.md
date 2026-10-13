# Etapa 5: mapa de atrasos e frequencias

Os atrasos de 50, 100 e 200 us passaram em todas as condicoes testadas. Com 350 us houve falhas a 500 e 1000 Hz. Com 500 us houve falhas nessas duas frequencias e, em algumas condicoes, o controle piorou o desempenho em relacao ao pilar desligado. A demonstracao isolada de 350 us acertou 17/17, mas o ensaio ampliado a 500 Hz acertou 66/68; isso mostra por que precisamos de mais de uma trajetoria.

Os resultados descrevem os pontos avaliados do modelo. Nao estabelecem uma faixa continua garantida, um atraso maximo universal ou um limite para um circuito fisico.

## Demonstracao

Abra MLC_mapa_demo.cir no LTspice com o filtro All Files, mantendo MLC_mapa.inc na mesma pasta. Clique em Run e adicione V(x) e V(saida). Para acompanhar o pilar, adicione V(perturbacao), V(ajuste) e I(Bcorrecao).

| Passo da demonstracao | Atraso ou condicao | Acertos na demonstracao |
|---|---|---:|
| 1 | 50 us | 17/17 |
| 2 | 100 us | 17/17 |
| 3 | 200 us | 17/17 |
| 4 | 350 us | 17/17 |
| 5 | 500 us | 9/17 |
| 6 | Pilar desligado | 16/17 |

Essa demonstracao usa perturbacao de 500 Hz e um estado inicial. Use Select Steps para mostrar apenas duas curvas por vez. O grafico mapa_funcionamento.svg mostra o conjunto ampliado abaixo.

## Metodo fixado antes das execucoes

Mantivemos a porta AND da revisao 2, limiar zero, corrente maxima de +/-20 uA, constante de tempo da resposta de 100 us e erro da replica de +0,02%. O amortecimento recebe uma perturbacao senoidal de amplitude +/-0,5%.

Variamos frequencia entre 100, 500 e 1000 Hz e latencia entre 50, 100, 200, 350 e 500 us. Acrescentamos o controle desligado em cada frequencia. Cada configuracao teve x inicial=-0,37/+0,37, y inicial=-0,2, e passos maximos de 5 e 2,5 us.

Sao 72 trajetorias, com 17 janelas cada: 1224 janelas no ensaio principal. A demonstracao acrescenta seis trajetorias e 102 janelas. Cada sequencia cobre todas as 16 transicoes possiveis entre os quatro pares de entradas, sem reiniciar o estado entre blocos.

As entradas duram 50 ms. Acomodacao de 30 ms e leitura de 30 a 49 ms de cada bloco. Uma janela so passa se x permanece do lado correto de zero nos extremos calculados pelo LTspice. Mantivemos o criterio mesmo quando um grafico parecia satisfatorio. As trajetorias sao deterministas e as contagens nao sao probabilidades de confiabilidade de hardware.

## Mapa de acertos

Cada celula tem 68 janelas, de quatro trajetorias.

| Latencia | Perturbacao 100 Hz | Perturbacao 500 Hz | Perturbacao 1000 Hz |
|---|---:|---:|---:|
| 50 us | 68/68 | 68/68 | 68/68 |
| 100 us | 68/68 | 68/68 | 68/68 |
| 200 us | 68/68 | 68/68 | 68/68 |
| 350 us | 68/68 | 66/68 | 60/68 |
| 500 us | 68/68 | 43/68 | 50/68 |
| Desligado | 68/68 | 66/68 | 68/68 |

Com 350 us a 500 Hz, duas de quatro trajetorias completas passaram. Com 350 ou 500 us a 1000 Hz, nenhuma trajetoria inteira passou. Todas as trajetorias com os atrasos de 50, 100 e 200 us passaram nesse conjunto.

## Margem e necessidade do controle

Nao basta olhar o numero de acertos. A menor margem de x ate zero a 1000 Hz caiu de aproximadamente 0,20717 com 50 us para 0,15404 com 100 us e 0,05038 com 200 us. Esses tres casos acertaram todas as janelas, mas o ultimo teve menor folga nesse conjunto.

A 1000 Hz, o pilar desligado tambem acertou todas as janelas, com margem minima de aproximadamente 0,11643. O pilar de 50 us aumentou essa margem; o de 200 us reduziu-a; e os atrasos maiores produziram erros. A 100 Hz, o controle desligado tambem acertou todas as janelas. Portanto, nao demonstramos que o pilar seja necessario ou vantajoso em todas as condicoes.

O limite de corrente de 20 uA foi atingido e atuou nos casos controlados. As fracoes medias de tempo saturado nas janelas variaram aproximadamente entre 56% e 67%. O sucesso dos atrasos menores ocorreu mesmo com saturacao efetiva. Ainda nao medimos consumo total ou um custo fisico do controlador.

## Conclusao para a hipotese

Este ensaio sustenta que uma compensacao pode preservar a operacao logica em determinados casos e que sua temporizacao precisa ser considerada. Tambem mostra casos em que um pilar prejudica uma porta que acertaria sem ele. Isso e relevante para a proposta de varios pilares interligados: a coordenacao precisaria evitar correcao inadequada e nao pode ser avaliada apenas acrescentando mais atuadores.

Continuamos testando uma porta e um pilar de compensacao de parametro. A estrutura de nove pilares, nove subpilares e conexoes entre portas ainda nao foi implementada. Sua vantagem precisara ser medida contra controles mais simples e com restricoes comparaveis de corrente, sensores, atraso e custo.

## Proximo ensaio proposto

Antes de ampliar a rede, testar um segundo canal sob perturbacao independente e verificar se os dois controles cooperam. Manter inicialmente latencia de 50 us e resposta de 100 us como referencia, pois tiveram maior margem nos casos rapidos avaliados. Se a coordenacao trouxer melhora, estudar topologias maiores e falhas de sensores com orcamento total de controle equivalente.

Outra possibilidade e romper a correspondencia favoravel entre replica e parametro: variar o erro da replica no tempo e introduzir ruido. Esses ensaios ajudam a aproximar a pesquisa das exigencias de uma realizacao fisica.

## Arquivos preservados

- MLC_mapa_validacao.cir e MLC_mapa.inc: modelo e ensaio principal.
- casos_etapa5.json: casos especificados antes da execucao.
- resultados_etapa5.csv e resumo_etapa5.json: medidas, classificacoes, margens, saturacao e falhas.
- Arquivos .log e .raw: resultados LTspice 26.1.1.
- mapa_funcionamento.svg: mapa das contagens reais.

O documento PESQUISA_HIPOTESE_PILARES.md, na pasta superior, explica as aplicacoes candidatas, o valor de uma pesquisa por simulacao, os trabalhos relacionados e o que falta para testar a arquitetura original.
