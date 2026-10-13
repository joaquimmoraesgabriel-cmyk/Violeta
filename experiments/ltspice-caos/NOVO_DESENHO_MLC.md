# Novo desenho: AND por comportamento persistente, com um pilar

Abra **MLC_AND_pilar_demo_v2.cir** no LTspice. Esse e o arquivo recomendado para explorar o novo desenho. Ele executa duas vezes a mesma sequencia de entradas: primeiro com controle=0 (pilar desligado), depois com controle=1 (ligado).

O novo desenho passou nos ensaios realizados com o pilar: 918 de 918 janelas no conjunto usado durante o desenvolvimento e 136 de 136 janelas num ensaio novo, realizado depois de fixar a revisao. Isso e evidencia numerica limitada a esses casos; nao demonstra uma montagem fisica nem a arquitetura completa de nove pilares e nove subpilares.

## Ver no LTspice

1. Use File > Open, filtro All Files, e abra MLC_AND_pilar_demo_v2.cir. Mantenha MLC_base_v2.inc na mesma pasta: o arquivo principal carrega esse modelo.
2. Clique em Run.
3. Em Add Trace, adicione V(x). Ha uma curva por execucao.
4. Use View > Step Legend ou Select Steps no menu do grafico para identificar controle=0 e controle=1. Os nomes dos menus podem variar entre versoes.
5. Adicione V(entrada_a), V(entrada_b) e V(saida), preferencialmente em outro painel de grafico. V(saida) vale 1 quando x>0 e 0 quando x<=0.
6. Para ver o pilar, adicione V(ajuste). Sua tensao representa o ajuste normalizado estimado; nao e um comando de aumentar ou diminuir um volt inteiro.

Cada par de entradas fica aplicado por 50 ms. Reservamos os primeiros 30 ms para acomodacao. Avaliamos o intervalo de 30 a 49 ms de cada bloco, inteiro. Oscilacoes ou resultados diferentes durante a transicao nao contam como erros nesse criterio; essa espera faz parte do desenho e precisa ser respeitada ao usar a porta.

Um trecho facil de observar:

| Tempo | A | B | AND desejada | Janela avaliada |
|---|---:|---:|---:|---|
| 500 a 550 ms | 0 | 1 | 0 | 530 a 549 ms |
| 550 a 600 ms | 1 | 1 | 1 | 580 a 599 ms |
| 600 a 650 ms | 1 | 0 | 0 | 630 a 649 ms |

Na demonstracao, sem o pilar houve 14/17 janelas corretas; com ele houve 17/17. A sequencia completa contem todas as 16 transicoes possiveis entre os quatro pares de entradas, incluindo repeticoes de um mesmo par.

O grafico MLC_comparacao.svg mostra curvas reais do LTspice nesse trecho, com menos pontos apenas para facilitar a visualizacao.

## Como a porta decide

Usamos um modelo comportamental das equacoes do oscilador MLC, com dois estados x e y e uma excitacao senoidal. As entradas alteram um pequeno termo aplicado a esse sistema. A operacao e AND:

| A | B | Resultado |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 0 | 0 |
| 1 | 1 | 1 |

Para representar 0, x deve permanecer negativo durante toda a janela avaliada. Para representar 1, x deve permanecer positivo. As oscilacoes continuam, mas a classificacao usa a regiao em que elas acontecem. Nenhum valor de tensao aos 11 ou 12 ms e usado como referencia.

O limiar de leitura e zero, fixo em todos os ensaios. A resposta esperada e usada apenas na analise posterior dos resultados. O controlador nao recebe a tabela verdade nem corrige a saida com base numa resposta fornecida externamente.

O modelo tem fontes comportamentais ideais e capacitores que integram as equacoes. x e y sao grandezas normalizadas representadas por tensoes no simulador. A escala de tempo de 100 us e uma escolha de representacao; os tempos e amplitudes daqui nao sao uma especificacao de uma montagem fisica pronta.

## Como funciona o pilar

Variamos em +/-0,5% o parametro de amortecimento, que regula a dissipacao na equacao de y. Uma replica resistiva acompanha a variacao desse parametro. Uma ponte com uma referencia ideal de 1 V e um resistor padrao estima a variacao da replica. A fonte Bcorrecao acrescenta um termo proporcional a y para compensar esse desvio.

Com referencia perfeita, a compensacao cancela esse desvio matematicamente. Para evitar depender apenas desse caso ideal, tambem testamos a replica com erro multiplicativo de -0,02% e +0,02%. Ainda supomos que replica e parametro compartilham a mesma variacao principal e que o resistor padrao e a fonte de referencia sao estaveis.

Este e um pilar de compensacao baseado numa medicao de parametro, com comandos de ajuste positivos ou negativos. Ainda nao e um controlador hierarquico do erro logico, nem uma rede de portas conectadas entre si. Sua hipotese motivou o objetivo de preservar a operacao enquanto o circuito oscila; a estrutura completa continua por definir e testar.

## Resultados da revisao final

Cada execucao tem 17 janelas de leitura, cobrindo uma sequencia continua sem reiniciar o estado entre entradas.

| Ensaio | Execucoes completas corretas | Janelas corretas |
|---|---:|---:|
| Sem pilar: estados x=-1,0,+1; amortecimento -0,5%,0%,+0,5%; passos 5 e 2,5 us | 6/18 | 264/306 |
| Com pilar, replica com erro -0,02%, mesmos estados/desvios/passos | 18/18 | 306/306 |
| Com pilar, replica ideal, mesmos estados/desvios/passos | 18/18 | 306/306 |
| Com pilar, replica com erro +0,02%, mesmos estados/desvios/passos | 18/18 | 306/306 |
| Verificacao nova, depois de fixar o desenho | 8/8 | 136/136 |

A verificacao nova inverteu a sequencia, usou x inicial=-0,37/+0,37, y inicial=-0,2, desvios de amortecimento de -0,37%/+0,37%, erros de replica de -0,0137%/+0,0137% e passo maximo de 1,25 us. Os parametros da porta e o criterio de acerto permaneceram fixos. O menor afastamento de x de zero nas janelas controladas foi aproximadamente 0,27775 no conjunto de desenvolvimento e 0,27870 no ensaio novo.

Uma janela so passa se o sinal de x permanece correto nos extremos medidos pelo LTspice durante todo o intervalo. Nao usamos apenas a media nem relaxamos o criterio para ignorar pequenas falhas depois de observar os resultados. Como toda simulacao numerica, esse teste examina a solucao calculada com passos finitos; nao prova uma propriedade para todos os tempos reais.

Os 918 casos sao janelas de 54 trajetorias deterministicas, e nao 918 testes aleatorios independentes. As contagens nao sao uma probabilidade de funcionamento em hardware. O conjunto de desenvolvimento foi reutilizado para melhorar a revisao; o ensaio novo foi separado e realizado sem reajustar os parametros.

## O que mudou durante o desenvolvimento

A primeira versao MLC usava entrada_amp=0,002 e bias=-0,002. Com o pilar, acertou 901/918 janelas e apenas 38/54 trajetorias inteiras. Preservamos esses arquivos e resultados.

A revisao 2 aumentou entrada_amp para 0,005 e ajustou bias para -0,005. A excitacao senoidal permaneceu em 0,11. Isso deu maior margem para a mudanca entre regioes. Mantivemos as janelas, os limiares e as perturbacoes da avaliacao.

## Ainda existe caos?

Uma estimativa independente, por integracao RK4 do estado e do vetor tangente das mesmas equacoes, calculou o maior expoente de Lyapunov sob entradas constantes e parametros nominais. Descartamos 1000 unidades de tempo normalizado e medimos quatro blocos de 1000 unidades. Repetimos com passos normalizados de 0,02 e 0,01.

Na revisao 2, os valores medios com passo 0,01 foram:

| Entrada | Maior expoente estimado, por unidade de tempo normalizado |
|---|---:|
| 00 | -0,04575 |
| 01 ou 10 | +0,02382 |
| 11 | +0,02815 |

O sinal dos expoentes foi o mesmo nos dois passos e nos quatro blocos. Ha evidencia numerica de dinamica caotica nos casos 01/10 e 11. Para 00, o resultado nao indica caos e e compativel com uma resposta periodica estavel ao sinal externo. Portanto, a porta pode passar entre comportamentos diferentes; nao afirmamos que todas as entradas mantem caos. Essa estimativa e complementar aos resultados LTspice e nao uma prova rigorosa dos atratores.

## Limites e proximos ensaios

Ainda faltam ruido aleatorio, perturbacoes variando durante uma mesma entrada, erros do resistor padrao e da referencia de tensao, atrasos e saturacao do atuador, varias frequencias e amplitudes, outras sequencias e tempos de acomodacao, implementacao com componentes reais e portas interligadas. A variacao de amortecimento e um teste de parametro; nao simulamos temperatura fisica.

O resultado sustenta continuar investigando essa implementacao minima. O proximo passo para os pilares e aplicar perturbacoes que mudam ao longo do tempo e verificar se a correcao ainda funciona com atraso e limitacao de corrente, antes de ampliar a rede.

## Arquivos e referencia

- MLC_AND_pilar_demo_v2.cir: demonstracao recomendada, dois passos.
- MLC_base_v2.inc: equacoes e parametros da porta, carregados pela demonstracao.
- MLC_AND_validacao_v2.cir: ensaio sem pilar.
- MLC_AND_pilar_validacao_v2.cir: ensaio com pilar e tres erros de replica.
- MLC_AND_verificacao_nova_v2.cir: verificacao nova.
- MLC_resultados.csv e MLC_resumo.json: resultados de cada janela e resumos, incluindo a primeira versao.
- MLC_lyapunov_v2.json: estimativas independentes de Lyapunov.
- Os arquivos .log e .raw preservam as medidas e curvas geradas pelo LTspice.

Referencia conceitual e das equacoes: Murali et al., *Chaotic Attractor Hopping yields Logic Operations*, https://arxiv.org/abs/1811.10029 . O artigo descreve uma leitura de resultados por atratores em regioes distintas. Implementamos suas equacoes como modelo ideal, com escala de tempo escolhida e uma compensacao adicional propria. Na nossa implementacao, bias negativo produziu AND; a legenda da Fig. 2 atribui AND a bias positivo. Usamos o comportamento observado nas equacoes implementadas, sem alegar reproducao exata daquela figura ou do circuito experimental do artigo.
