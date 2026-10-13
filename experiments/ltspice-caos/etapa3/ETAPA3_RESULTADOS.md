# Etapa 3: perturbacao durante o calculo, atraso e limite de corrente

O pilar com latencia de 50 us, resposta de primeira ordem de 100 us e limite de +/-100 uA manteve a leitura correta em todas as 204 janelas avaliadas. A versao mais lenta e fraca manteve as respostas sob mudancas lentas e alternadas, mas falhou sob oscilacao rapida: 40/68 janelas corretas, contra 66/68 sem controle nessa condicao.

Este ensaio mostra uma melhora e uma condicao de falha no modelo. Ainda nao estabelece limites gerais de atraso ou corrente, nem demonstra uma realizacao fisica ou a rede completa de nove pilares.

## Arquivos para abrir

- **MLC_dinamico_demo.cir:** mudancas alternadas durante a janela de leitura; quatro modos para comparar.
- **MLC_dinamico_limite.cir:** perturbacao rapida; permite observar as falhas do modo mais lento e fraco.
- MLC_dinamico.inc: modelo carregado automaticamente; deve ficar na mesma pasta.

Abra um arquivo .cir no LTspice com o filtro All Files e clique em Run. Depois adicione V(x) e V(saida). Para acompanhar o pilar, adicione V(perturbacao), V(ajuste) e I(Bcorrecao), de preferencia em paineis separados.

| Passo na demonstracao | Parametro modo | Controle |
|---|---:|---|
| 1 | 0 | Desligado |
| 2 | 1 | Reacao instantanea, sem limite de corrente |
| 3 | 2 | Latencia 50 us, resposta 100 us, limite +/-100 uA |
| 4 | 3 | Latencia 500 us, resposta 1 ms, limite +/-20 uA |

Use Step Legend ou Select Steps no menu do grafico para mostrar apenas os passos desejados. Os nomes dos menus podem variar entre versoes.

No arquivo MLC_dinamico_demo.cir, o intervalo de 630 a 649 ms corresponde a A=1, B=0: x deve permanecer negativo. Esse trecho conteve uma falha sem o pilar e passou com o pilar do modo 2. O grafico comparacao_etapa3.svg mostra as curvas reais nesse intervalo. O trecho foi selecionado para ilustrar uma falha; o desempenho total esta na tabela abaixo.

Na demonstracao com mudancas alternadas, os passos acertaram 16/17, 17/17, 17/17 e 17/17 janelas, respectivamente. Na demonstracao rapida, acertaram 16/17, 17/17, 17/17 e 8/17.

## O que mudou no modelo

A porta continua com as equacoes e parametros da revisao 2: entradas de amplitude normalizada 0,005 por bit, bias=-0,005, excitacao senoidal de amplitude 0,11 e leitura pelo sinal de x. Variamos agora o parametro de amortecimento durante a simulacao.

A replica resistiva acompanha a perturbacao e tem um erro multiplicativo fixo de +0,02%. A estimativa da variacao passa por um atraso puro e um filtro RC, representando uma resposta que leva tempo para acompanhar a medicao. A fonte de correcao aplica uma corrente limitada nos modos 2 e 3. O modo 1 serve de comparacao com resposta instantanea e corrente sem limite; sua replica ainda tem o erro de +0,02%.

O controlador usa a medicao da replica e o estado y. Ele nao recebe a resposta AND esperada. A perturbacao e aplicada ao sistema e a replica pelo mesmo sinal, uma hipotese de acompanhamento que continua precisando de verificacao numa montagem fisica.

As correntes e tempos sao valores do modelo comportamental escalado. Ainda nao especificam amplificadores, sensores ou componentes de uma realizacao fisica.

## Perturbacoes definidas antes do teste

Todas alteram o amortecimento em ate +/-0,5%:

1. Senoide lenta: 5 Hz, periodo de 200 ms.
2. Alternancia: transicoes de 100 us entre -0,5% e +0,5%, aproximadamente a cada 25 ms. A primeira subida ocorre aos 35 ms e as seguintes repetem a cada 50 ms; essas mudancas acontecem dentro das janelas avaliadas.
3. Senoide rapida: 500 Hz, periodo de 2 ms.

Essas sao perturbacoes abstratas de um parametro. Temperatura fisica e ruido aleatorio nao foram modelados nesta etapa.

## Criterio e conjunto de avaliacao

A sequencia de entradas tem 17 blocos de 50 ms e cobre todas as 16 transicoes entre 00, 01, 10 e 11. O estado continua entre os blocos. Os primeiros 30 ms de cada bloco ficam reservados para acomodacao. A janela avaliada vai de 30 a 49 ms, inteira.

Uma janela passa somente se o sinal de x permanece correto nos extremos calculados pelo LTspice: negativo para 00, 01 e 10; positivo para 11. O limiar continua em zero. Mantivemos esse criterio em todos os modos e nao relaxamos a leitura depois de ver falhas.

Foram 48 trajetorias no ensaio principal: 3 perturbacoes x 4 modos x 2 estados iniciais x 2 passos maximos. Os estados iniciais sao x=-0,37/+0,37, y=-0,2; os passos maximos sao 5 e 2,5 us. Sao 816 janelas no total e 204 por modo. As duas demonstracoes acrescentam 8 trajetorias e 136 janelas.

As trajetorias sao deterministicas, com uma mesma sequencia de entradas. As contagens nao sao ensaios aleatorios independentes nem uma probabilidade de sucesso em hardware. Os passos de tempo menores sao uma verificacao limitada de sensibilidade numerica, nao uma prova rigorosa da solucao continua.

## Resultado principal

Cada celula abaixo tem 68 janelas, de quatro trajetorias de 17 blocos.

| Perturbacao | Desligado | Instantaneo | Atrasado, +/-100 uA | Mais lento, +/-20 uA |
|---|---:|---:|---:|---:|
| Senoide de 5 Hz | 66/68 | 68/68 | 68/68 | 68/68 |
| Alternancia de aproximadamente 25 ms | 61/68 | 68/68 | 68/68 | 68/68 |
| Senoide de 500 Hz | 66/68 | 68/68 | 68/68 | 40/68 |
| Total | 193/204 | 204/204 | 204/204 | 176/204 |

Contando trajetorias inteiras, sem nenhuma janela errada: 5/12 sem controle, 12/12 no modo instantaneo, 12/12 no modo 2 e 8/12 no modo 3. Todas as quatro trajetorias do modo 3 com perturbacao rapida tiveram alguma falha.

O menor afastamento de x de zero no modo 2 foi aproximadamente 0,22309, na perturbacao rapida. A margem permaneceu positiva em todas as suas janelas.

## Corrente e acompanhamento

O pico de corrente do modo 2 foi aproximadamente 76,51 uA; portanto, seu limite de 100 uA nao chegou a atuar neste conjunto. O teste demonstra o funcionamento com esse limite presente, mas nao prova tolerancia a saturacao nesse modo.

O modo 3 atingiu efetivamente o limite de 20 uA. A fracao media de tempo saturado nas janelas foi aproximadamente 64,24% com perturbacao lenta, 88,75% na alternancia e 3,27% com perturbacao rapida.

Mesmo com pouca saturacao no caso rapido, o modo 3 apresentou maior erro de acompanhamento e falhas logicas. Ele altera conjuntamente latencia, constante de tempo e limite de corrente: nao isolamos a contribuicao de cada fator. Nao podemos atribuir todas as falhas exclusivamente ao atraso ou exclusivamente a corrente disponivel.

O resultado evidencia que acrescentar um controle nao garante uma melhora em todas as condicoes: a versao lenta e fraca teve desempenho inferior ao controle desligado na perturbacao rapida. Isso precisa ser considerado antes de interligar varios pilares ou portas.

## Proximo ensaio

Antes de ampliar a rede, podemos separar os fatores: manter a corrente disponivel fixa e variar o atraso; depois manter o atraso fixo e variar a corrente. Isso permite identificar uma faixa de funcionamento para esse pilar e escolher condicoes para testar dois pilares interagindo.

Ainda faltam ruido, erros independentes entre parametro e replica, deriva da referencia de tensao e do resistor padrao, atrasos variaveis, outras sequencias, outras amplitudes, varias portas e realizacao com componentes reais. A dinamica caotica foi estimada para o modelo nominal na etapa anterior; nao reestimamos Lyapunov para cada perturbacao variavel desta etapa.

## Evidencias preservadas

- resultados_etapa3.csv: medidas e acerto de cada janela.
- resumo_etapa3.json: resumo por perfil e modo, com lista de falhas.
- casos_etapa3.json: especificacao dos 48 casos definida antes das simulacoes.
- MLC_dinamico_validacao.cir: arquivo do ensaio principal.
- Arquivos .log e .raw: medidas e curvas geradas pelo LTspice 26.1.1.
- comparacao_etapa3.svg: comparacao visual de curvas reais da demonstracao.

Referencia tecnica para as fontes comportamentais e funcoes de atraso e limitacao: documentacao oficial da Analog Devices, https://github.com/analogdevicesinc/ltspice-reference/blob/main/ai_ref/CIRCUIT-ELEMENTS-REFERENCE.md .
