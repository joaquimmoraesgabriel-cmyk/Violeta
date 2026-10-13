# Etapa 8: limites e quando nove subpilares fazem sentido

Encontramos uma utilidade especifica para nove subpilares: tolerar quatro medicoes defeituosas usando a mediana. Cinco e sete falharam nessa condicao; nove passaram nas duas condicoes iniciais e nos passos maximos de 5 e 2,5 us. Para duas falhas, cinco ja bastaram. Isso avalia redundancia de medicao de um parametro, nao comprova nove pilares de correcao nem a rede completa 9x9.

O outro ensaio mostrou que atraso e capacidade de correcao sao limites distintos. No perfil avaliado, o coordenador com limite de 100 uA passou com 0 e 100 us de atraso adicional; falhou com 500 us e 1 ms. Dar 200 uA nao recuperou as condicoes com atrasos maiores. As contagens nao variam de forma monotona, portanto nao identificamos um atraso maximo exato.

## O que pilar e subpilar significam neste ensaio

Ainda existem dois pilares de atuacao: A corrige amortecimento e B corrige bias. Mantivemos o sensor de A; no sensor de B, variamos o numero de replicas participantes em 1, 3, 5, 7 e 9. O pilar B recebe a mediana dessas leituras, depois usa o filtro e o atuador anteriores. A mediana e calculada por ordenacao de nove sinais explicitamente modelados, selecionando quantos participam. O arquivo e uma rede superset com selecao de sensores; nao estima area ou consumo de realizacoes diferentes.

Os sensores saudaveis medem a mesma replica ideal de perturbacao, todos com offset -0,0002. Uma falha adiciona +0,020 unidades normalizadas a uma leitura, permanentemente. Os primeiros f sensores sao afetados. Nao e uma falha de 0,020 V garantida em hardware. Os sensores saudaveis tem leituras identicas; nao incluimos ruido independente, deriva variavel, erros de ganho ou desconexao eletrica.

A regra nao conhece a tabela AND e nao recebe V(referencia) ou V(ler). Ela apenas combina medicoes. Conferimos separadamente, nos dados RAW da demonstracao, que a estimativa unica contaminada tem desvio +0,020 e que as medianas de 3 e 9 recuperam a leitura saudavel com diferenca numerica menor que 1e-7 (excluindo o ponto de inicializacao uic em t=0). A verificacao esta em verificacao_mediana.json.

## Ensaio de atraso e capacidade

Mesma porta MLC e perfil assimetrico da etapa 7: perturbacao de amortecimento +/-0,15% a 500 Hz; bias +/-0,010 a 137 Hz, fase 40 graus. Os sensores continuam tendo latencia de 50 us e resposta de 100 us. O atraso abaixo e ADICIONAL, aplicado aos pedidos de corrente ja repartidos pelo coordenador, antes do atuador. Um limite comum instantaneo protege o orcamento mesmo durante transicoes; nao e um modelo de circuito fisico dessa protecao.

Divisao fixa: metade da capacidade para cada canal, sem o atraso adicional de coordenacao. Coordenado: reparte proporcionalmente a demanda e atrasa os dois pedidos. Cada celula tem 34 janelas: duas trajetorias, x inicial=-0,37/+0,37, y=-0,2, passo maximo=5 us.

| Capacidade nominal total (uA) | Divisao fixa | Coordenador 0 us | 100 us | 500 us | 1000 us |
|---|---|---|---|---|---|
| 50 | 23/34 | 27/34 | 32/34 | 27/34 | 13/34 |
| 100 | 33/34 | 34/34 | 34/34 | 19/34 | 16/34 |
| 200 | 34/34 | 34/34 | 34/34 | 21/34 | 12/34 |

O resultado com 50 uA e 100 us foi melhor na contagem que o de atraso zero, mas ambos tiveram falhas. Isso impede transformar estes pontos num limite monotono ou dizer que todo atraso prejudica. Com 100 uA, a menor margem positiva passou de aproximadamente 0,247 sem atraso a 0,139 com 100 us no passo de 5 us. Mais acertos e maior margem sao indicadores distintos.

## Ensaio de subpilares e falhas

Mesmo perfil, coordenador sem atraso adicional e capacidade nominal de 100 uA para todos os numeros de sensores. O numero de sensores aumenta recursos de medicao, mas nao a corrente maxima de atuacao. Nao igualamos o consumo nem o custo da mediana ou das replicas. Cada celula abaixo tem 34 janelas, passo de 5 us.

| Sensores participantes N | Sem falha | 1 falha | 2 falhas | 4 falhas | Todos N com erro |
|---|---|---|---|---|---|
| 1 | 34/34 | 26/34 | nao se aplica | nao se aplica | 26/34 |
| 3 | 34/34 | 34/34 | 26/34 | nao se aplica | 26/34 |
| 5 | nao ensaiado | nao ensaiado | 34/34 | 26/34 | nao ensaiado |
| 7 | nao ensaiado | nao ensaiado | 34/34 | 26/34 | nao ensaiado |
| 9 | 34/34 | 34/34 | 34/34 | 34/34 | 26/34 |

Quando todos os nove recebem o mesmo deslocamento, a mediana fica errada e a porta falha. Esse caso equivale a um erro comum de medicao; repeticao nao fornece uma referencia independente. Para 5 e 7, a condicao de todos com erro nao foi ensaiada.

## Refinamento numerico

Estas condicoes tambem foram executadas com passo maximo de 2,5 us, mantendo as mesmas tolerancias do solver.

| Condicao | Janelas corretas | Menor margem de x ate zero |
|---|---|---|
| atraso=0 us, limite=100 uA | 34/34 | 0.247792 |
| atraso=100 us, limite=100 uA | 34/34 | 0.151713 |
| atraso=1000 us, limite=100 uA | 15/34 | -1.419531 |
| N=5, falhas=2 | 34/34 | 0.246233 |
| N=5, falhas=4 | 26/34 | -1.474624 |
| N=7, falhas=2 | 34/34 | 0.246233 |
| N=7, falhas=4 | 26/34 | -1.474624 |
| N=9, falhas=4 | 34/34 | 0.246233 |
| N=1, falhas=1 | 26/34 | -1.474624 |
| N=3, falhas=1 | 34/34 | 0.246233 |
| N=3, falhas=2 | 26/34 | -1.474624 |
| N=9, falhas=1 | 34/34 | 0.246233 |
| N=9, falhas=2 | 34/34 | 0.246233 |

Na comparacao janela a janela das execucoes refinadas contra o passo de 5 us, houve 5 janelas com classificacao alterada. O caso com atraso de 1 ms passou de 16/34 para 15/34; continua falhando. Os casos de mediana pareados mantiveram as classificacoes de acerto/falha; as trajetorias e margens nao precisam ser identicas. Os intermediarios 5 e 7 tambem mantiveram as contagens entre os dois passos.

Tolerancias: reltol=1e-6, vntol=1e-9, abstol=1e-12. A maior ultrapassagem medida da capacidade nominal foi 0.001006457 uA. O analisador preserva os picos e aceita ate 0,005 uA de ultrapassagem numerica, sem alegar garantia fisica. Capacidade maxima e consumo de energia nao sao a mesma coisa.

## Quando escolher nove, e quando nao

Para esta regra de mediana, sob a premissa de sensores saudaveis concordando, a maioria precisa continuar saudavel. Para tolerar f leituras arbitrariamente erradas, a quantidade minima e N=2f+1: uma falha pede 3; duas pedem 5; tres pedem 7; quatro pedem 9. E uma propriedade de redundancia da mediana, nao um resultado exclusivo da computacao por caos. O ensaio verificou deslocamentos positivos definidos, nao todos os tipos de falha arbitraria.

Assim, nove subpilares se justificam se o requisito for manter a medicao correta mesmo com quatro dessas falhas, e se o custo e o atraso forem aceitaveis. Se o requisito for apenas uma ou duas falhas, este ensaio nao justifica nove: tres ou cinco entregaram o mesmo acerto. Se todos compartilham o erro, nove nao bastam.

Nove PILARES sao outra pergunta. Hoje so corrigimos dois desvios distintos. Antes de criar mais canais, precisamos identificar quais perturbacoes cada novo pilar mede e corrige, comparar a estrutura menor e verificar que os atuadores nao se atrapalham. Copiar o mesmo canal nove vezes nao introduz automaticamente nove informacoes ou nove correcoes uteis.

Para considerar a arquitetura completa 9x9 util, exigir uma tarefa e uma faixa de perturbacoes previamente definidas; testar redes menores e remover partes da maior; medir trajetorias inteiras corretas, margem, tempo de acomodacao, tolerancia a falhas e custo total. A escolha deve ser a menor estrutura que cumpre os requisitos. Nem o numero nove nem o ganho de redundancia demonstrado validam as conexoes entre todas as portas, ainda ausentes.

## Quantidade e criterio de leitura

Ensaio principal e refinamentos: 86 trajetorias e 1462 janelas. Demonstracao adicional: 3 trajetorias e 51 janelas. Os casos de limite e 1/3/9 foram definidos antes das suas simulacoes; 5/7 e o refinamento de nove com quatro falhas foram extensoes declaradas depois dos primeiros resultados, nao testes cegos de uma arquitetura selecionada.

Cada trajetoria tem 17 blocos de 50 ms cobrindo as 16 transicoes entre 00, 01, 10 e 11 sem reiniciar o circuito. Ignoramos os primeiros 30 ms e avaliamos os extremos de x de 30 a 49 ms: x estritamente positivo para 11 e negativo nos demais casos. Uma media correta nao compensa um pulso errado dentro da janela. Sao contagens deterministas, nao probabilidades de confiabilidade. Os extremos sao de uma solucao numerica finita, nao uma prova continua.

Nao repetimos a analise de Lyapunov para estas perturbacoes; oscilacoes ou acertos nao provam caos em cada condicao. Nao testamos temperatura fisica, componentes reais, ruído de alimentacao, falhas do combinador, atraso proprio da mediana ou varias portas acopladas. A medicao de bias continua sendo uma replica favoravel que separa a perturbacao das entradas logicas.

## Ver a demonstracao no LTspice

Abra MLC_subpilares_demo.cir com MLC_subpilares.inc na mesma pasta. Run gera tres passos: 1 sensor, 3 sensores e 9 sensores, todos com uma leitura defeituosa. Resultados: 13/17, 17/17 e 17/17, respectivamente.

Em Select Steps, escolha um passo por vez. Adicione V(saida), V(referencia) e V(ler). A resposta deve coincidir com a referencia durante V(ler)=1. Em outro painel, compare V(sub1), V(sub2), V(sub3) e V(estimativa_b): o primeiro sensor e o defeituoso, os demais sao saudaveis. Com um sensor participante, a estimativa segue o ruim; com tres ou nove, segue os saudaveis.

## Evidencias e reproducao

- Modelos MLC_limites.inc e MLC_subpilares.inc e os sete decks .cir.
- Arquivos .json com casos de cada deck, definidos antes das respectivas execucoes.
- Logs e RAW do LTspice, resultados_ensaios.csv e resumo_ensaios.json.
- verificar_sensores.py e verificacao_mediana.json: conferencia independente das estimativas no RAW da demonstracao.
- comparacao_refinamento.json: janelas cuja classificacao mudou no refinamento.
- preparar_ensaios.py prepara o conjunto inicial; preparar_intermediarios.py e preparar_quatro_falhas.py preparam extensoes. Rodar cada deck em batch no LTspice e analisar todos os nomes de decks com analisar_ensaios.py, depois verificar_sensores.py e gerar_relatorio.py.

O proximo ensaio deve desafiar a premissa das replicas: erros diferentes nos sensores saudaveis, perturbacao comum e atraso do combinador. Isso determina se a vantagem observada permanece com medicoes menos favoraveis, antes de ampliar o numero de parametros corrigidos ou interligar portas.
