# Etapa 7: coordenador e leitura dos graficos

O coordenador ajudou quando o canal B precisava de mais corrente: acertou 68/68 janelas, contra 63/68 com a divisao fixa. No perfil que exige mais do canal A, houve melhora de 65/68 para 67/68, ainda com uma falha. Sob demanda elevada nos dois, ambos falharam e a regra proporcional ficou em 29/68, contra 31/68 da divisao fixa.

Este resultado apoia investigar coordenacao, mas nao demonstra que a regra proporcional seja melhor em todas as condicoes. Ainda avaliamos uma porta, dois canais e uma camada simples de alocacao, nao a arquitetura completa de nove pilares e nove subpilares.

## Como entender o sobe e desce

V(x) e o movimento interno do circuito. Sua amplitude pode variar e oscilar sem mudar o resultado logico. O resultado deste modelo e V(saida): 1 quando x esta acima de zero, 0 quando esta abaixo ou igual a zero.

Para AND, esperamos 1 somente quando as duas entradas sao 1. Para os demais pares, esperamos 0. A linha V(referencia) e um monitor dessa resposta esperada, usado para observar; ela nao entra nos controles nem no coordenador.

Cada entrada fica aplicada durante 50 ms. Reservamos 30 ms para acomodacao, depois avaliamos 19 ms. V(ler)=1 marca a janela de leitura. Mudancas fora dessa janela podem ser transicoes permitidas pelo criterio; dentro da janela, uma passagem para o lado errado de zero conta como falha. Esse tempo de espera faz parte do desenho, e nao deve ser esquecido ao interligar portas.

## Ver no LTspice

Abra **MLC_coordenador_demo.cir**, mantendo MLC_coordenador.inc na mesma pasta, e clique em Run. Sao tres execucoes:

| Passo | Politica | Resultado da demonstracao |
|---|---:|---:|
| 1 | Controle desligado | 10/17 |
| 2 | Dois canais, divisao fixa | 16/17 |
| 3 | Dois canais e coordenador | 17/17 |

Comece com uma unica execucao no Select Steps. Em Add Trace, adicione V(saida) e V(referencia). Observe se as duas linhas coincidem durante V(ler)=1. Depois adicione V(x) em outro painel para relacionar a leitura 0/1 com o movimento interno.

Um exemplo concreto e o bloco de 350 a 400 ms: A=0 e B=1, entao esperamos 0. Avaliamos 380 a 399 ms. Na demonstracao, a divisao fixa teve uma breve passagem de x acima de zero nessa janela; V(saida) mostrou um pulso 1 indevido. O coordenador passou nessa janela inteira. Mostrar todas as execucoes e todos os sinais sobrepostos esconde essa diferenca.

As oscilacoes visiveis, sozinhas, nao demonstram caos. A estimativa de Lyapunov da etapa anterior foi para parametros nominais; nao repetimos essa analise para todas as perturbacoes desta etapa.

## Regra do coordenador

Os dois canais usam as mesmas medicoes, atraso de 50 us e resposta de 100 us. A divisao fixa permite ate 50 uA por canal. O coordenador examina as correntes solicitadas: se a soma dos modulos nao exceder 100 uA, permite ambas por inteiro; se exceder, reduz ambas na mesma proporcao para respeitar o orcamento nominal.

Assim, um canal pode usar capacidade que ficaria ociosa na divisao fixa. O coordenador nao sabe a resposta AND correta e nao usa V(referencia) ou V(ler). Essa e uma regra de recursos, nao uma otimizacao direta do erro logico. A camada de coordenacao e instantanea neste modelo; seu proprio atraso e custo ainda precisam ser testados.

## Metodo e perfis definidos antes do teste

A porta, as entradas e o criterio de leitura permaneceram os da revisao 2. O canal A corrige o amortecimento; o B corrige um desvio no termo de bias. As perturbacoes sao senoides separadas: A a 500 Hz; B a 137 Hz, fase inicial de 40 graus. Nao modelamos independencia estatistica ou ruido aleatorio.

| Perfil | Amplitude A | Amplitude B, normalizada |
|---|---:|---:|
| Equilibrado | +/-0,5% | +/-0,006 |
| B exige mais | +/-0,15% | +/-0,010 |
| A exige mais | +/-1,0% | +/-0,001 |
| Demanda elevada nos dois | +/-1,5% | +/-0,012 |

Cada perfil teve tres politicas: desligado, divisao fixa e proporcional. Cada politica foi executada com x inicial=-0,37/+0,37, y inicial=-0,2, passos maximos de 5 e 2,5 us, erro multiplicativo da replica A de +0,02% e erro aditivo da replica B de -0,0002.

Sao 48 trajetorias, com 17 blocos de entrada cada: 816 janelas. A sequencia cobre todas as 16 transicoes entre os quatro pares de entradas, sem reiniciar o estado entre blocos. As contagens sao deterministas, nao probabilidades de confiabilidade de hardware. A demonstracao acrescenta tres trajetorias e 51 janelas.

## Resultado completo

Cada celula tem 68 janelas, de quatro trajetorias.

| Perfil | Desligado | Divisao fixa | Coordenador |
|---|---:|---:|---:|
| Equilibrado | 41/68 | 68/68 | 68/68 |
| B exige mais | 29/68 | 63/68 | 68/68 |
| A exige mais | 31/68 | 65/68 | 67/68 |
| Demanda elevada nos dois | 0/68 | 31/68 | 29/68 |
| Total | 101/272 | 227/272 | 232/272 |

Trajetorias inteiras corretas: 0/16 desligado, 6/16 divisao fixa, 11/16 coordenador. No perfil equilibrado, ambos acertaram todas as janelas, mas a menor margem caiu de aproximadamente 0,19114 na divisao fixa para 0,17283 no coordenador. Portanto, a coordenacao nao melhorou todos os indicadores nem todas as condicoes.

## Precisao e limite de corrente

Usamos reltol=1e-6, vntol=1e-9 e abstol=1e-12, mais estritos que na etapa 6, em todas as politicas. Uma execucao preliminar com tolerancias anteriores mostrou pequena ultrapassagem numerica do monitor de corrente e motivou esse refinamento. Os resultados finais nao devem ser comparados como trajetorias identicas aos da etapa 6, pois mudaram tolerancias, monitores e perfis.

O orcamento nominal e 100 uA. O maior pico registrado foi 100,001729152 uA, aproximadamente 0,00173 uA acima, no monitor numerico. Preservamos esse valor e usamos uma tolerancia explicita de verificacao de 0,005 uA. Isso e uma tolerancia para o ensaio numerico, nao uma margem fisica garantida. Nao alegamos que as medidas tenham sido exatamente menores ou iguais a 100 em todos os pontos.

O modelo de reparticao limita matematicamente a soma dos modulos das demandas aplicadas. Ainda precisamos avaliar uma realizacao com circuito fisico, propria dinamica, atrasos, tolerancias e fonte de energia. Igualamos o orcamento nominal de corrente, nao o consumo, a area ou o custo total.

## Proximos ensaios e limites

As replicas ainda acompanham diretamente os desvios de parametro, com erros definidos. Falta testar deriva independente, ruido, atrasos do coordenador, falhas de sensores e uma regra que priorize canais em vez de reduzir ambos proporcionalmente. A demanda elevada mostrou uma condicao em que essa regra pode piorar a leitura, portanto aumentar camadas exige novas comparacoes.

Para continuar a pesquisa, comparar a reparticao proporcional com outras regras sob o mesmo orcamento e introduzir atraso na camada superior. O acerto das mesmas janelas, por si, nao demonstrara vantagem de uma hierarquia maior; precisamos medir margem, tolerancia a falhas e custo.

## Evidencias

- MLC_coordenador_demo.cir: demonstracao com monitores de leitura.
- MLC_coordenador_validacao.cir e MLC_coordenador.inc: ensaio principal e modelo.
- casos_etapa7.json: casos especificados antes da execucao.
- resultados_etapa7.csv e resumo_etapa7.json: medidas, classificacao, margens, picos e falhas.
- Arquivos .log e .raw: resultados do LTspice 26.1.1.

O guia interativo na conversa usa as curvas reais da demonstracao, agrupadas para caber na visualizacao. Os extremos de cada agrupamento sao preservados como faixa; as classificacoes exibidas usam as medidas completas do LTspice.
