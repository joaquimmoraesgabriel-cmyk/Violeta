# Teste inicial dos pilares de controle

O primeiro prototipo nao demonstrou uma porta logica confiavel. Houve uma melhora com compensacao ideal, mas ela desapareceu com erro de referencia. A leitura logica tambem mudou ao refinar o passo de simulacao. Esses resultados nao validam nem refutam a arquitetura completa de nove pilares e nove subpilares: avaliam uma implementacao minima e especifica de um pilar.

Simulacoes executadas no LTspice 26.1.1, em 11 de outubro de 2026. Foram 3 execucoes de calibracao e 188 execucoes de avaliacao. Parte delas repete condicoes identicas; as contagens nao representam ensaios aleatorios independentes nem probabilidades de funcionamento no mundo real.

## Circuito e criterio de acerto

Usamos o modelo ideal de Chua anterior. Cada entrada A e B injeta 10 uA de 10 a 11 ms. Cada simulacao comeca do mesmo estado. Sao avaliadas as combinacoes 00, 01, 10 e 11, em execucoes independentes. Nao ha processamento continuo de uma sequencia de bits.

A calibracao comparou cinco instantes de leitura, selecionando 11 ms como um candidato com separacao entre a resposta de soma=2 e as demais. Com passo maximo de 100 ns, o limiar escolhido foi 0,6419474952615 V. A leitura e 1 quando V(v2) esta abaixo do limiar e 0 quando esta acima. O limiar fica fixo em todos os testes seguintes: nao e reajustado usando respostas do conjunto de avaliacao.

No caso nominal, com a mesma configuracao numerica da calibracao:

| A | B | V(v2) aos 11 ms | Resultado | AND esperada |
|---|---|---:|---:|---:|
| 0 | 0 | 0,666818637372 V | 0 | 0 |
| 0 | 1 | 0,651999425291 V | 0 | 0 |
| 1 | 0 | 0,651999425291 V | 0 | 0 |
| 1 | 1 | 0,631895147999 V | 1 | 1 |

Isso e uma classificacao temporal calibrada, nao a demonstracao de uma porta fisica robusta. O sinal V(saida) no grafico e um comparador instantaneo e pode oscilar; apenas sua leitura aos 11 ms e avaliada. Nao implementamos um registrador que guarde o resultado.

## O pilar testado

Uma replica do resistor R1 acompanha sua variacao. Uma ponte alimentada por uma referencia ideal de 1 V mede a replica. A fonte Bcorrecao acrescenta ou retira corrente entre v1 e v2, tentando restaurar a condutancia nominal dessa ligacao. O controlador usa somente V(sensor), V(v1) e V(v2). Ele nao recebe A*B ou um sinal da resposta correta. A*B aparece apenas na avaliacao posterior das medidas.

Tecnicamente este pilar e uma compensacao baseada na medicao de um parametro, nao a hierarquia de realimentacao do erro logico proposta pelo usuario. Sem erro da replica, a compensacao cancela matematicamente a variacao de R1 no modelo ideal. Esse sucesso isolado e esperado pela construcao; nao prova tolerancia geral a perturbacoes.

## Variacao de resistencia

Variamos R1 em -1,5%, -1%, -0,5%, 0%, +0,5%, +1% e +1,5%. Em cada valor executamos as quatro entradas, com controle desligado e ligado: 56 simulacoes.

| Condicao da referencia | Acertos sem controle | Acertos com controle |
|---|---:|---:|
| Replica ideal | 10/28 | 28/28 |
| Replica com erro de -0,02% | 10/28 | 7/28 |
| Replica com erro de +0,02% | 10/28 | 7/28 |

As duas linhas com erro da replica correspondem a mais 112 simulacoes. O erro e aplicado multiplicativamente ao valor da replica, nao como ruido aleatorio. Nesses casos, com controle ligado, a leitura foi 1 para todas as quatro combinacoes; so 11 acertou. A menor margem ideal era aproximadamente 10,05 mV.

## Dependencia do passo numerico

Com R1 nominal e controle desligado, repetimos as quatro entradas com passos maximos menores, mantendo o limiar original. Foram 20 simulacoes.

| Passo maximo | Acertos nas quatro entradas |
|---|---:|
| 100 ns | 4/4 |
| 50 ns | 0/4 |
| 25 ns | 1/4 |
| 12,5 ns | 1/4 |
| 6,25 ns | 1/4 |

Portanto, o sucesso nominal calibrado a 100 ns nao persistiu no refinamento. Nao demonstramos convergencia completa da solucao, nem uma classificacao independente das escolhas numericas. A leitura instantanea apos um longo transiente caotico e inadequada neste prototipo para estabelecer confiabilidade.

## Limites e proximo desenho

Este ensaio nao modelou temperatura fisica, ruido aleatorio, atrasos de controle, limites de amplificadores ou de fontes, variacoes dos capacitores e indutor, nem portas interligadas. A variacao de R1 e apenas uma perturbacao de componente que pode servir de ensaio inicial. A replica e o resistor padrao ainda exigiriam uma realizacao fisica e caracterizacao.

A ideia dos pilares continua uma hipotese de pesquisa. Antes de ampliar a rede, precisamos definir uma porta cuja leitura tenha uma margem confiavel. Uma direcao e codificar 0 e 1 em comportamentos distintos e persistentes, em vez de depender da tensao num unico instante. Depois podemos calibrar controles com entradas de teste conhecidas e avaliar, separadamente, as quatro entradas sob perturbacoes e refinamento numerico.

Referencia dessa direcao, sem alegar que a reproduzimos neste ensaio: Murali et al., Chaotic Attractor Hopping yields Logic Operations, https://arxiv.org/abs/1811.10029 . Os autores investigam a codificacao de resultados em atratores que ocupam regioes distintas.

## Abrir e conferir no LTspice

1. Abra Hipotese_pilar_AND.cir usando o filtro All Files e clique em Run. Sao 56 passos.
2. Abra View > SPICE Error Log e veja resultado, esperado e erro. Erro=0 e acerto; erro=1 e falha.
3. Abra Hipotese_pilar_AND_sensor.cir para executar o ensaio com as duas imprecisoes da replica (112 passos).
4. Abra Hipotese_AND_precisao.cir para executar o refinamento numerico (20 passos).
5. Para inspecionar curvas, adicione V(v2), V(sensor), V(saida) e I(Bcorrecao). Use Select Steps para comparar passos. No arquivo principal, caso=0..3 e controle desligado a -1,5%; caso=4..7 e controle ligado a -1,5%; caso=24..27 e nominal desligado; caso=28..31 e nominal ligado. No log, o numero de passo comeca em 1; o parametro caso comeca em 0.

As execucoes podem levar alguns minutos e gerar arquivos de curvas grandes. Os resultados obtidos ja estao em resultados_hipotese.csv, resumo_hipotese.json e nos logs do LTspice. O analisador so le as medidas geradas pelo programa; nao inventa curvas nem resultados.
