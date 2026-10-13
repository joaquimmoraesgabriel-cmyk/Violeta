# Etapa 6: dois canais de correcao

Os dois canais acertaram todas as 204 janelas do conjunto principal e todas as 12 trajetorias completas. Quando as duas perturbacoes atuaram juntas, acertaram 68/68, contra 63/68 do melhor canal sozinho. O limite maximo total de corrente de atuacao permaneceu em 100 uA. Isso sustenta continuar investigando a combinacao desses dois canais no modelo; ainda nao valida uma hierarquia ou a estrutura completa de nove pilares.

## Demonstracao

Abra **MLC_dois_pilares_demo.cir** no LTspice com o filtro All Files e clique em Run. Mantenha MLC_dois_pilares.inc na mesma pasta. Adicione V(x) e V(saida), e use Select Steps para comparar duas execucoes por vez.

| Passo | Topologia | Canais ligados |
|---|---:|---|
| 1 | 0 | Nenhum |
| 2 | 1 | Apenas A: amortecimento |
| 3 | 2 | Apenas B: deslocamento de bias |
| 4 | 3 | A e B |

Para acompanhar as perturbacoes e os ajustes, adicione V(pert_a), V(pert_b), V(ajuste_a) e V(ajuste_b). Para ver as correntes, adicione I(Bcorrecao_a) e I(Bcorrecao_b), de preferencia em paineis separados. A orientacao das fontes e diferente: A injeta corrente no estado y; B retira corrente para compensar o desvio de bias.

V(orcamento) representa numericamente a soma dos modulos das duas correntes, em ampere. O valor 0,0001 corresponde a 100 uA; esse monitor nao e uma alimentacao de 100 uV.

## Pergunta do ensaio

Dois canais que corrigem parametros diferentes conseguem preservar a operacao AND quando duas perturbacoes atuam juntas, mantendo a mesma capacidade total de corrente de correcao?

Esta etapa compara canais independentes na mesma porta. Ainda nao implementa um coordenador hierarquico, varias portas conectadas ou os nove pilares e nove subpilares da proposta original.

## Perturbacoes e sensores

- A altera o amortecimento em +/-0,5%, com senoide de 500 Hz.
- B altera o termo de bias em +/-0,006 unidades normalizadas, com senoide de 137 Hz e fase inicial de 40 graus.

Sao fontes separadas, com parametros e frequencias distintos. Nao sao ruido aleatorio e nao avaliamos independencia estatistica. Testamos A isolada, B isolada e as duas simultaneamente.

A usa a replica resistiva anterior, com erro multiplicativo de +0,02%. B usa uma replica ideal do desvio de bias com erro aditivo de -0,0002 unidades normalizadas. Cada leitura tem latencia de 50 us e resposta de primeira ordem de 100 us. As fontes de correcao possuem limitacao de corrente.

A replica de B fornece uma medida do desvio indesejado, separada das entradas logicas. Isso e uma hipotese favoravel do modelo que ainda exige implementacao e verificacao: num circuito real, sera preciso distinguir uma deriva do parametro de uma mudanca legitima causada pela entrada. Os controles nao recebem a resposta AND desejada.

## Comparacao de recursos

Com um canal ligado, ele pode usar ate +/-100 uA. Com dois, cada um pode usar ate +/-50 uA. Assim, a soma dos modulos das correntes aplicadas permanece limitada a 100 uA nos casos controlados.

O monitor de orcamento e medido ao longo de toda a simulacao, e o analisador verifica que esse limite nao foi excedido. Comparar a soma dos modulos impede que correntes de sentidos opostos escondam o uso de recursos por cancelamento.

Isso iguala a capacidade maxima de atuacao, nao o custo completo dos controladores. Ainda nao medimos consumo, area ou custo de dois sensores e dois atuadores em hardware.

## Metodo

A porta e a leitura permanecem as da revisao 2: mesma amplitude de entrada, bias nominal, forca senoidal e limiar zero. Cada sequencia tem 17 blocos de 50 ms e cobre todas as 16 transicoes entre os pares 00, 01, 10 e 11, sem reiniciar o estado entre blocos.

Reservamos os primeiros 30 ms de cada bloco para acomodacao e avaliamos todo o intervalo de 30 a 49 ms. Uma janela passa se os extremos calculados pelo LTspice mantem x negativo para 00/01/10 ou positivo para 11.

O ensaio completo tem 48 trajetorias: 3 perfis de perturbacao x 4 topologias x 2 estados iniciais x 2 passos maximos. Os estados sao x=-0,37/+0,37, y=-0,2; os passos sao 5 e 2,5 us. Sao 816 janelas no ensaio principal. A demonstracao acrescenta quatro trajetorias e 68 janelas.

Os casos foram definidos antes das simulacoes. As contagens sao de trajetorias deterministas e nao representam probabilidades de sucesso em hardware. A avaliacao por extremos e baseada na solucao numerica com passos finitos, nao numa prova de sinal para todos os instantes reais.

## Resultados

Cada celula tem 68 janelas de quatro trajetorias.

| Perturbacoes aplicadas | Sem controle | So A | So B | A e B |
|---|---:|---:|---:|---:|
| Apenas amortecimento (A) | 62/68 | 68/68 | 62/68 | 68/68 |
| Apenas bias (B) | 33/68 | 43/68 | 68/68 | 68/68 |
| As duas juntas | 41/68 | 42/68 | 63/68 | 68/68 |
| Total | 136/204 | 153/204 | 193/204 | 204/204 |

Contando trajetorias completas sem nenhuma janela errada: 0/12 sem controle, 4/12 com A, 7/12 com B e 12/12 com ambos.

A demonstracao isolada acertou 11/17 sem controle, 8/17 com A, 17/17 com B e 17/17 com ambos. O ensaio ampliado identificou falhas do canal B sozinho que nao apareceram nessa primeira trajetoria.

Com as perturbacoes juntas e ambos os canais ligados, a menor margem de x ate zero foi aproximadamente 0,14925. Com B sozinho, a menor margem no conjunto ficou negativa, aproximadamente -0,03582. Na demonstracao, que passou com B sozinho, a margem era de apenas 0,01499; com ambos, era 0,14925.

## Orcamento, saturacao e interpretacao

Com ambos ligados sob perturbacoes simultaneas, a soma dos modulos das correntes chegou a aproximadamente 100 uA, sem exceder o limite. A saturacao nas janelas ocorreu por cerca de 12,39% do tempo no canal A e 36,68% no canal B. Mesmo com essas limitacoes efetivamente atuando, todas as janelas desse grupo passaram.

O melhor canal sozinho chegou a aproximadamente 61,78 uA. Portanto, igualamos o limite maximo permitido, mas nao o uso efetivo de corrente ou o consumo de energia. Os dois canais podem gastar mais recursos reais e exigem mais hardware. A melhora nao demonstra uma vantagem de consumo ou de area.

As perturbacoes modificam partes distintas da dinamica. Corrigir apenas uma delas deixa o outro desvio atuando. O resultado sustenta que cobrir os dois desvios com canais dedicados pode preservar a operacao neste conjunto. Nao demonstra que qualquer segundo pilar ajude, nem que canais adicionais sejam sempre melhores.

Mesmo sem perturbacao de amortecimento, o erro da replica A produz uma pequena correcao espuria; o mesmo ocorre com B sem perturbacao de bias. Esses ajustes podem alterar a dinamica e explicar diferencas de contagem entre topologias que parecem nao tratar a perturbacao principal. Ainda precisamos testar erros de sensor variaveis e independentes em vez de offsets fixos.

## Proximo passo

Comparar a divisao fixa de 50 uA por canal com um coordenador que redistribui um orcamento total de 100 uA conforme a corrente solicitada por cada canal. O coordenador deve usar medicoes e demandas de correcao, sem receber a resposta logica esperada. Isso introduzira uma camada acima dos dois canais e permitira estudar uma parte da hierarquia sugerida na hipotese.

Para medir uma vantagem de coordenacao, testar tambem condicoes em que um canal precisa de mais corrente e o outro tem capacidade ociosa. Manter o mesmo orcamento maximo e criterio de leitura e relatar casos em que a coordenacao ajuda, nao muda ou prejudica o resultado. As condicoes desta etapa ja passaram com divisao fixa, portanto acertar novamente as mesmas janelas nao bastaria para mostrar uma vantagem do coordenador.

## Evidencias e limites

Os modelos ainda usam fontes comportamentais e replicas com relacao conhecida com as perturbacoes. Nao avaliamos ruido, temperatura fisica, deriva independente das replicas, interconexao entre portas, varias regras de coordenacao ou realizacao com componentes reais. Nao reestimamos Lyapunov para todas as perturbacoes desta etapa.

- MLC_dois_pilares_validacao.cir e MLC_dois_pilares.inc: ensaio principal e modelo.
- casos_etapa6.json: configuracoes definidas antes da execucao.
- resultados_etapa6.csv e resumo_etapa6.json: medidas, classificacao, margens, saturacao, orcamento e falhas.
- Arquivos .log e .raw: dados gerados pelo LTspice 26.1.1.
- comparacao_dois_pilares.svg: mapa das contagens reais.
