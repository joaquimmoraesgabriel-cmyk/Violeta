# Proposta de ativacao seletiva dos nove subpilares

Estado: desenho anterior aos testes de selecao. Um prototipo foi posteriormente comparado na etapa 9; os resultados da etapa 8 pertencem a selecoes fixas.

Atualizacao posterior: a etapa 9 implementou e comparou nove fixos, tres fixos, rodizio, sorteio e um seletor adaptativo 3/9 com disponibilidade e tempo de despertar simulados em software, alimentando a porta no LTspice. Consulte ../etapa9/ETAPA9_RESULTADOS.md. O restante deste documento preserva o desenho proposto antes desses testes; nao representa circuitos fisicos ja implementados.

## O que o modelo atual faz

O LTspice calcula nove fontes comportamentais de medicao. O parametro nsub escolhe quantas contribuem para a mediana, e fica constante durante cada execucao. Nao ha desligamento de alimentacao, economia de energia medida, rodizio ou despertar de sensores. Nove disponiveis e nove participantes sao conceitos distintos.

## Interpretacao candidata: redundancia com reserva

Um grupo pode trabalhar simultaneamente e os grupos podem se alternar ao longo do tempo. Para os subpilares de medicao de bias da etapa 8, a proposta e manter normalmente tres participantes e usar os demais como reserva e para verificacoes. Tres e um ponto inicial para comparar, nao a quantidade ideal ja demonstrada para operacao adaptativa.

Um supervisor recebe leituras, divergencia entre leituras, estado de prontidao de cada sensor e um relogio de verificacao. Ele nao recebe a resposta AND esperada, o numero real de sensores defeituosos ou a identidade dos defeituosos.

1. **Inicializacao/verificacao:** acordar os sensores a comparar e esperar que suas leituras fiquem validas. Uma verificacao completa pode usar os nove por um intervalo curto. O custo desse intervalo deve ser contado.
2. **Operacao normal:** usar tres participantes selecionados na verificacao. Os outros ficam em reserva. A mediana destes tres fornece a estimativa ao mesmo filtro e atuador.
3. **Suspeita:** divergencia acima de um limiar durante tempo suficiente solicita reforco, por exemplo cinco e depois nove. O numero necessario nao e conhecido antecipadamente. Este mecanismo sozinho pode perder falhas concordantes; dois sensores ruins do trio podem concordar entre si.
4. **Verificacao periodica:** acordar reservas mesmo sem alarme, para desafiar a concordancia aparente do grupo ativo. Com nove validos, usar a mediana como referencia interna e marcar as leituras que se afastam dela. Essa referencia pressupoe uma maioria saudavel e falha com erro comum.
5. **Retorno:** depois de varias verificacoes consistentes, selecionar novamente um grupo menor que concorde com a referencia interna. Usar limiares diferentes para subir e descer a quantidade e um tempo minimo em cada estado, evitando comutacao rapida.

Uma variacao faz verificacoes por grupos de tres, sem acordar nove simultaneamente. Nesse caso, as leituras sao tomadas em momentos diferentes: nao podem ser combinadas como se fossem instantaneas quando o sinal esta mudando. Precisam de timestamps, modelo temporal ou uma tarefa que permita tempo suficiente para a comparacao. A protecao instantanea contra quatro falhas obtida com nove leituras da etapa 8 nao e automaticamente preservada.

## Tres formas de selecionar

| Regra | Funcao | Limite a investigar |
|---|---|---|
| Rodizio determinista | Alternar grupos ou testar reservas em ordem conhecida | Demora ate visitar um sensor e efeito das trocas |
| Sorteio com semente registrada | Variar os grupos sem repetir sempre os mesmos | Pode escolher uma maioria defeituosa; registrar sementes e repetir ensaios |
| Ativacao por necessidade | Ampliar o grupo com divergencia e verificacoes | O supervisor pode nao detectar erros compartilhados ou concordantes |

O sorteio nao fornece a mesma garantia da mediana com maioria saudavel. Para quatro falhas entre nove, um grupo de tres ou cinco pode ter maioria defeituosa. A quantidade economizada traz um risco e uma demora de deteccao que precisam ser medidos, mesmo se a selecao for aleatoria.

## Outra interpretacao: subpilares especializados

Em vez de replicas da mesma medicao, cada subpilar pode corrigir uma causa diferente e receber um gatilho especifico. Por exemplo, um canal para deriva termica, outro para alimentacao e outro para erro de sensor, depois de definir o que mede e como atua. Um observador precisa continuar funcionando para perceber quando acordar cada canal.

Essa arquitetura tem outra funcao: os subpilares nao estao votando sobre a mesma grandeza. Nove canais especializados nao herdam a regra N=2f+1 dos sensores redundantes. Tambem e possivel uma estrutura hibrida, com canais especializados e redundancia de medicao dentro de alguns deles. As causas e interfaces ainda precisam ser modeladas; temperatura fisica ainda nao foi implementada.

## Ensaio necessario para dizer se compensa

Comparar nove fixos, tres fixos, rodizio e ativacao adaptativa nas mesmas sequencias, capacidade de atuacao e condicoes iniciais. Usar falhas que aparecem e desaparecem em sensores de posicoes distintas, erros que concordam, erro comum, ruido e tempo de despertar. Separar casos usados para definir limiares dos usados para avaliar a regra.

Medir janelas e trajetorias corretas, margem, numero medio e maximo de participantes, tempo entre falha e deteccao, periodos sem leitura valida e quantidade de trocas. O numero medio de participantes e um indicador de uso, nao uma medida de energia. Economia real exige alimentacao, sensores, supervisor e custos de despertar definidos.

O controlador deve ser comparado sem saber quais sensores falharam. Se a simulacao ligar exatamente os sensores saudaveis usando o parametro de falha, isso seria uma selecao privilegiada e nao uma demonstracao de adaptacao.
