# O que investigar com a hipotese dos pilares

## Atualização: laboratório e Etapa 19 concluídos

O ChaosLab separa cálculo em malha fixa, observação, armazenamento compacto e
interface Streamlit. O lote auditado tem 41 ensaios e 71.156 janelas, incluindo
sete conjuntos de 10.000 janelas. Esses conjuntos compartilham entradas e
condições iniciais para comparações pareadas; não são 71.156 testes independentes.

A concessão efetiva sob desvio de cotas avançou de 7.218 para 7.287 acertos em
10.000 janelas, com 528 recuperações e 459 regressões. Saudável, empatou com
os controles em 7.151/10.000, preservando estados finais e tabelas de janelas.
Persistem seis alarmes indevidos em oito trajetórias dos cantos combinados.
O refino também continua aberto: 24/34 em duas malhas esconde 16 discordâncias.

As ablações não permitem atribuir toda a perda à equação, ao orçamento ou ao
atraso físico isoladamente: a referência ilimitada cancela em cada subpasso RK4,
enquanto o controle limitado é amostrado. L2/comum também mudam política e
tempos juntos. Esses controles causais devem preceder uma escolha definitiva.
O teto de corrente do laboratório é algébrico, sem validação de chips ou PCB.

Resultados, hipóteses e prioridades estão no
[relatório da Etapa 19](etapa19/ETAPA19_RESULTADOS.txt) e na
[síntese da candidata](PIRAMIDE_CANDIDATA.md).
O [guia do laboratório](../../chaoslab/GUIA.txt) explica reprodução e uso do painel.
Os RAWs concluídos removidos para liberar espaço foram substituídos por fontes,
métricas e extratos conforme o
[registro de retenção](manutencao_armazenamento/NOTA_RETENCAO.txt).

## Objetivo

Investigar se uma estrutura de controles locais e coordenacao em camadas pode preservar a operacao logica de elementos nao lineares sob perturbacoes, com custo de controle aceitavel.

A proposta original inclui nove pilares por porta, nove subpilares por pilar e conexoes entre portas. Ainda precisamos definir o que cada elemento mede, o que consegue ajustar, como combina as medicoes, com qual atraso e como evita correcao conflitante. O numero nove e uma escolha de arquitetura a investigar, nao uma necessidade demonstrada pela dinamica.

## Estado atual

Os primeiros ensaios usam uma porta AND comportamental baseada nas equacoes MLC e um pilar de compensacao. O pilar mede uma replica que acompanha um parametro e corrige seu efeito. Isso avalia uma parte da motivacao da ideia: manter a resposta logica enquanto o sistema continua oscilando.

A etapa 6 acrescentou um segundo canal, que corrige um desvio de bias enquanto o primeiro trata o amortecimento. Os dois juntos acertaram 204/204 janelas nas condicoes avaliadas, mantendo o mesmo limite maximo total de corrente. Sob as duas perturbacoes simultaneas, o melhor canal sozinho acertou 63/68 e ambos acertaram 68/68. Os sensores ainda sao replicas favoraveis com erros definidos; nao igualamos consumo ou custo completo de hardware.

A etapa 7 introduziu um coordenador de corrente acima dos dois canais. No perfil em que o bias exige mais correcao, passou de 63/68 para 68/68 janelas; sob demanda elevada nos dois, ficou pior que a divisao fixa. A etapa 8 testou atraso adicional e capacidade: com 100 uA, passou com 0 e 100 us adicionais, mas falhou com 500 us e 1 ms; duplicar a capacidade nao recuperou os atrasos maiores. Isso nao determina um limite exato nem monotono.

A etapa 8 tambem deu uma interpretacao parcial aos subpilares: sensores redundantes de bias combinados por mediana. Tres bastaram para uma leitura defeituosa, cinco para duas; com quatro leituras deslocadas, cinco e sete falharam e nove passaram, inclusive com passo de tempo menor. Quando todos os nove tiveram o mesmo erro, falharam. Sao replicas saudaveis com leituras identicas e falhas positivas fixas, sem custo ou atraso fisico do combinador. A regra N=2f+1 explica a maioria saudavel; nao e uma vantagem exclusiva de caos. Continuam ausentes nove parametros corrigidos, a arquitetura completa 9x9 e a conexao entre portas. Consulte etapa8/ETAPA8_RESULTADOS.md para medidas e limites.

A etapa 9 comparou selecao fixa, rodizio, sorteio e adaptacao de sensores de bias, incluindo erros individuais, ruido determinista, falhas temporarias em posicoes distintas e despertar de 200 us. No cenario de quatro falhas, o adaptativo teve 34/34 janelas como nove fixos, usando media de 3,731 ligados; ambas as contagens foram preservadas em passo de 2,5 us. Rodizio ficou em 27/34; sorteio em 24/34, 26/34 e 28/34. O adaptativo usa verificacoes completas breves, nao evita sempre nove simultaneos. Todos falharam com erro comum. O supervisor e externo, causal e amostrado; quantidade de participantes nao mede energia real. Consulte etapa9/ETAPA9_RESULTADOS.md.

A etapa 10 definiu um terceiro canal para desvio na amplitude da excitacao e comparou as oito combinacoes de A/B/C sob a mesma capacidade nominal de corrente. Ele melhorou a margem no desvio menor e a contagem relativa no forte em quatro passos maximos. Contudo as contagens fortes variaram com passo e houve falha em 0,625 us, impedindo afirmar convergencia quantitativa e confiabilidade total. Sensores e atuadores continuam comportamentais e favoraveis. A combinacao do seletor adaptativo com tres pilares ainda nao foi ensaiada. Consulte etapa10/ETAPA10_RESULTADOS.md.

O modelo pressupoe uma relacao conhecida entre perturbacao, replica e atuador. Mesmo com erro da replica, essa relacao ainda e favoravel e precisa ser desafiada com erros independentes, ruido e componentes reais. Os ensaios de atraso, resposta e saturacao sao passos para explicitar as condicoes em que a compensacao falha.

A etapa 11 definiu D para deriva multiplicativa da curva nao linear g(x), com atuacao no estado x. No desvio isolado de +/-1%, D passou em 34/34 janelas nos passos 2,5, 1,25 e 0,625 us; sem ele houve falhas nos tres. A etapa 12 comparou um coordenador comum, dois grupos AB/CD, emprestimo, prioridade e reserva local sob 100 uA. O comum teve a maior contagem sem falha (259/272, igualado pela reserva), mas nenhuma regra garantiu funcionamento sob todas as falhas. A reserva nao percebeu parada com heartbeat mantido e piorou sob atraso permanente.

A etapa 13 compara somar os pedidos de A/B/C antes da alocacao e aplicar uma unica corrente em y, mantendo D em x. Isso altera a arquitetura de atuacao, conservando as quatro funcoes de estimacao. A conferencia independente de etapa12/MEDICAO_CORRENTE.md distingue o pico exibido por V(orcamento) da soma das correntes: nos oito casos repetidos, o pequeno excesso do monitor nao foi confirmado acima do criterio de capacidade. Consulte os relatorios das etapas 11 a 13 para resultados e limites.

A etapa 14 implementou diagnostico por discrepancia com reserva retida. No perfil AB, a atuacao ideal com reserva passou em 340/340 janelas cobrindo saudavel e quatro defeitos do comando do topo, nos passos 2,5/1,25 us; sem reserva foram 313/340. A integracao com amplificadores genericos e shunts recuperou o silencio com heartbeat mantido: 34/34 contra 31/34, em passo 1,25 us. O limitador nao ideal exigiu isolamento de partida, reducao de saturacao ociosa e filtro RC. Seu candidato de 90 uA teve pico de 96,8 uA na bancada e 97,8 uA com tolerancias. Os modelos ainda nao definem chips reais, estabilidade completa ou parasitas da PCB. Dados e auditoria de consistencia da corrente estao em etapa14/ETAPA14_RESULTADOS.md.

A etapa 15 repetiu e ampliou a integracao nao ideal em 64 trajetorias (1.088 janelas), com passos 1,25/0,625 us. Todas respeitaram 100,005 uA pelos tres metodos de corrente; o pico por tensoes dos shunts foi 90,015769 uA. Com reserva: AB 340/340; equilibrado e CD 272/272; alta demanda 193/272. O topo saudavel em alta demanda ja falha (47/68) e gera tres alarmes indevidos, e varias classificacoes mudam com o passo. O controle complementar com atuacao ideal e mesmo RC chegou a 50/68 em 90 uA e 56/68 em 100 uA, mantendo falhas e alarmes indevidos. Os resultados deterministas nao sao uma probabilidade de confiabilidade; a boa contagem nos perfis moderados nao se estende a alta demanda. Evidencias e auditoria: etapa15/ETAPA15_RESULTADOS.md.

A auditoria posterior localizou uma carga entre os RCs da referencia do detector que nao existia no caminho de atuacao/medicao. Isolar os RCs com seguidores ideais eliminou os alarmes indevidos nas 28 trajetorias de regressao, preservando os limiares e o teto de corrente (pico 90,017140 uA). O candidato etapa15/MLC_filtros_isolados.inc manteve AB saudavel/silencioso em 136/136; alta demanda saudavel/silenciosa/atrasada/invertida ficou em 198/272 e o controle ideal corrigido em 53/68. A logica continua sensivel ao passo em alta demanda. A etapa totalizou 104 trajetorias validas (1.768 janelas), incluindo controles e repeticoes, sem substituir os resultados originais. Detalhes em etapa15/CORRECAO_FILTROS.md.

A meta futura registrada e construir uma placa virtual com modelos eletricos e termicos antes de fabricar. O roteiro de substituicao dos blocos ideais, validacao das malhas e inclusao de parasitas de layout esta em etapa14/PLANO_ETAPA14.md. A etapa 15 corrigiu a assimetria dos filtros, mas a margem logica sob alta demanda precisa de trabalho antes da selecao definitiva de componentes e do layout; nao tratar a aprovacao do modelo comportamental como aprovacao de hardware.

## Hipotese que pode ser comparada

Com a mesma tarefa logica, perturbacoes e restricoes de recursos, uma estrutura hierarquica de controle deve manter mais trajetorias inteiras corretas, ou ampliar a faixa de funcionamento, em relacao a uma estrutura mais simples.

Comparacoes essenciais: porta sem controle; um pilar; varios pilares independentes; pilares com coordenacao hierarquica; e uma topologia com o numero de conexoes reduzido. Para avaliar o efeito do numero de pilares, testar 1, 2, 3 e 9 com o mesmo orcamento total de corrente e medicoes, em vez de dar automaticamente mais recursos a maior rede.

Medir acertos da tabela verdade e de sequencias, margem entre classes, tempo de acomodacao, saturacao, custo do controlador e tolerancia a falhas. Um sistema maior que consome mais recursos para obter o mesmo resultado nao demonstra uma vantagem de arquitetura.

## Aplicacoes candidatas, se houver uma vantagem demonstrada

1. Blocos logicos que ajustam suas condicoes de operacao para tolerar deriva e perturbacoes.
2. Elementos reconfiguraveis, usando diferentes ajustes para implementar outras operacoes. Cada operacao precisaria ser validada separadamente.
3. Pequenas redes logicas, comparadores e somadores, depois de definir interfaces, temporizacao e acoplamento entre as portas.
4. Uma direcao distinta de computacao dinamica para reconhecer padroes temporais de sensores. Isso exigiria um modelo e uma leitura treinada proprios, possivelmente um reservatorio dinamico, e nao decorre automaticamente do nosso circuito AND.

Nao medimos vantagem sobre circuitos digitais convencionais em velocidade, consumo ou area. Esses criterios precisam de implementacoes equivalentes e do custo completo dos sensores e controles.

## O que a simulacao pode entregar por si

- Um modelo definido e reproduzivel, em vez de uma analogia apenas.
- Mapas das condicoes em que uma operacao funciona e em que falha.
- Comparacao entre topologias e mecanismos de controle, com testes retirando um componente por vez.
- Experimentos com ruido, erros independentes, variacoes de componentes, fontes, saturacao, atrasos e falhas de sensores.
- Redes pequenas que executem uma tarefa especifica, com entradas e resultados verificaveis.
- Estimativas de dinamica, como Lyapunov, quando adequadas, sem usar apenas a aparencia dos graficos como prova de caos.
- Um pacote de pesquisa com arquivos, parametros, resultados, analise e limites claros. Um estudo computacional pode ser util mesmo antes de uma montagem fisica, desde que as conclusoes fiquem dentro do que o modelo sustenta.

## Caminho para uma realizacao fisica

Converter os blocos comportamentais em uma implementacao com componentes especificos e alimentacao definida. Usar modelos desses componentes e incluir tolerancias, ruido e limites. Verificar separadamente a medicao, o atuador e a porta; montar uma porta com um pilar; e comparar medicoes com o modelo antes de aumentar a rede.

O objetivo da simulacao e reduzir incertezas e identificar exigencias da montagem. Ela nao representa automaticamente todos os efeitos de temperatura, capacitancias parasitas, envelhecimento, alimentacao, tolerancias, interferencia e instrumentos.

## Trabalhos relacionados e limites da busca

O principio geral de controlar sistemas caoticos e usar sua dinamica para calcular possui pesquisas anteriores. Isso fornece uma base e mecanismos de comparacao; nao demonstra que a estrutura exata de nove por nove seja conhecida, original ou vantajosa. A busca feita aqui foi direcionada, nao uma revisao exaustiva de originalidade.

- Ott, Grebogi e Yorke, *Controlling chaos* (1990): pequenas mudancas de parametros para obter comportamentos escolhidos. https://doi.org/10.1103/PhysRevLett.64.1196
- Sinha, Munakata e Ditto, *Flexible parallel implementation of logic gates using chaotic elements* (2002): operacoes logicas e exemplos de adicao em modelos caoticos. https://www.imsc.res.in/~sudeshna/PRE_13.pdf
- Murali et al., *Chaotic Attractor Hopping yields Logic Operations* (2018): resultados logicos associados a atratores em regioes distintas e verificacao em circuitos. https://arxiv.org/abs/1811.10029
- Du et al., *Reservoir computing using dynamic memristors for temporal information processing* (2017): exemplo de outra arquitetura de processamento dinamico, com tarefas de reconhecimento e dinamica temporal. https://pmc.ncbi.nlm.nih.gov/articles/PMC5736649/

## Proximos criterios de decisao

O segundo canal, a coordenacao e a selecao dinamica ja foram testados, com vantagens e falhas dependendo da condicao. A etapa 9 incluiu erros individuais, ruido, erro comum e despertar; falta varrer seus parametros, casos novos, custo, falha e atraso proprio do supervisor. Para decidir quantos subpilares usar, escolher a menor quantidade que cumpre uma tolerancia a falhas definida; quatro falhas motivam nove na regra de mediana avaliada, duas nao. A adaptacao pode reduzir a quantidade media, mas ainda usa nove em verificacoes e depende da disponibilidade das leituras.

Para decidir quantos pilares de atuacao usar, identificar novos desvios que os dois atuais nao corrigem, acrescentar canais com uma funcao mensuravel e comparar a retirada de cada canal, mantendo restricoes de recursos. Nove pilares nao ficam justificados apenas porque nove sensores toleram quatro falhas. A arquitetura completa precisa de tarefa, interfaces e temporizacao definidas antes da interconexao entre portas. O criterio para continuar e uma melhora reproduzivel com recursos e condicoes comparaveis.

## Etapa 16 — reserva local E dedicada a D

Foram concluidas 82 trajetorias novas no LTspice, alem da reanalise de 16 referencias corrigidas da etapa 15. Com o mesmo orcamento operacional de 90 uA, E revisado acertou 184/272 janelas de alta demanda, a referencia 198/272 e a prioridade em D com dois atuadores 189/272. E reduziu o residuo RMS da compensacao de D de 21.188 para 13.366 uA, mas o residuo do canal A-B-C passou de 40.717 para 49.579 uA. A variacao de g(x) ficou em 1001.34/1003.10 V/s do modelo (referencia/E); isso nao equivale a estresse termico.

As divergencias entre 1,25 e 0,625 us foram 42/136 na referencia e 40/136 em E. O terceiro passo de 0,3125 us ainda apresentou falhas. A reserva fixa de 20 uA ficou em 42/68 sem falha do topo. Uma cota exploratoria de E de 5 uA ficou em 49/68, contra 51/68 da referencia saudavel; esse ajuste nao foi expandido a todas as falhas ou ao terceiro passo.

A corrente passou nas 82 trajetorias novas pelas tres leituras, com pico pelos shunts de 90.025842 uA. A checagem previa encontrou uma inconsistência de cota na primeira reserva livre; a versao v2 a corrigiu, preservando os pilotos. Com perturbacoes em 75% e 50% da intensidade original, a referencia passou em 66/68 e 68/68. Isso delimita uma faixa mais favoravel, mas nao resolve o requisito de alta demanda original.

E tem nove leituras comportamentais e mediana explicita, ligadas apenas a sua funcao local de apoio a D. O comando E nao passa pelo topo; alimentacao e limitador continuam compartilhados. A saturacao utilizada e a falta de cota para atender D, nao uma falha fisica identificada no amplificador. A proposta completa tem 45 subpilares (5 x 9); A/B/C/D ainda usam replicas unicas neste lote. O conjunto de 45, o seletor adaptativo e chips/PCB permanecem por validar.

Manter E como candidato de reserva especializada, sem incorpora-lo como solucao aprovada para a alta demanda. O proximo foco e estudar a reparticao entre os estados x/y e a capacidade necessaria para preservar margem logica, com validacao em passos menores e condicoes novas. A referencia com dois atuadores continua disponivel. Relatorio: etapa16/ETAPA16_RESULTADOS.txt; grafico: etapa16/comparacao_pilar_E.svg; resultados completos e verificacao: etapa16/trajetorias.json, etapa16/janelas.csv e etapa16/verificacao_entrega.json.

## Etapa 17 — coordenador associado a E

Concluídas 64 trajetórias novas no LTspice, com orçamento operacional de 90 µA incluindo E (até 5 µA). Comparação funcional de coordenador comum e grupos ABC / D+E; cotas com transporte de 20 µs e filtro de 50 µs. Cotas complementares e arbitragem única impedem concessões duplicadas.

| Arquitetura | Janelas corretas | Corretas nos dois passos |
|---|---:|---:|
| Referência anterior | 198/272 | 78/136 |
| Comum com supervisor E | 199/272 | 80/136 |
| Grupos com empréstimo e supervisor E | 174/272 | 70/136 |

O saldo de uma janela no novo comum não demonstra ganho robusto; a sensibilidade ao terceiro passo permanece. A coordenação comum segue como base de pesquisa, com verificação da idade e da coerência das cotas ainda pendente.

Controle saudável 45/45: 38/68. Ajuste exploratório L2: 49/68 com filtro e 53/68 com cotas ideais instantâneas. O ajuste foi motivado pelo déficit em Y, sem acesso à resposta AND; não recebeu a matriz completa de falhas nem terceiro passo.

Corrente: pico físico 90.021849 µA; critério herdado <=100,005 µA. Falhas de heartbeat e soma de cotas têm fallback 45/45. Uma cota válida, mas enviesada, exige verificação distinta da discrepância entre comando e atuação. O supervisor continua sendo uma dependência compartilhada dos grupos.

Os resultados não validam chips/coordenadores fisicamente independentes, a pirâmide completa de 45 sensores ou PCB. Modelos antigos e ondas de referência foram preservados. Relatório e evidências: [Etapa 17](etapa17/ETAPA17_RESULTADOS.txt), [comparação](etapa17/comparacao_coordenadores.svg), [verificação](etapa17/verificacao_entrega.json).

## Etapa 18 — Fiscalizacao das cotas e recuperacao local

CONCLUSAO REVISADA

Manter um coordenador comum como referencia de arquitetura, com E como
reserva local e fiscal dentro do mesmo orcamento. O lote nao justifica
substitui-lo por dois coordenadores de grupos, nem declara o circuito
pronto. L2 com confirmacao V2 continua candidato de pesquisa.

O fiscal detectou 24/24 trajetorias com falha de cotas e comutacao
habilitada, sem contar memorias armadas antes da injecao. Isso inclui
heartbeat perdido, concessao dupla, cota extrema 0/90, desvio de ate
12 uA, atraso com carimbo antigo e cota antiga com carimbo recente.
Nas duas falhas simultaneas, os detectores de comando e de cota
atuaram; o detector de comando nao teve alarme indevido neste lote.
Esses resultados sao deteccao no modelo, nao tolerancia fisica de chips.

O limite mais importante encontrado foi a tolerancia do fiscal V1.
No comum nominal houve 0/4 alarmes indevidos; nos dois cantos combinando
RC, atraso, ruido e relogio houve 4/4 trajetorias saudaveis com alarme.
As idades permaneceram validas: a discrepancia de valores provocou a
comutacao, entre 2.238 e 2.332 ms. Nao e uma configuracao qualificada
para hardware. Nos quatro instantes de primeiro disparo, as cotas ainda
cobriam ambos os pedidos. Isso reforca a hipotese de fiscalizar a
concessao efetiva, sem provar que essa alternativa eliminaria o problema.
Os cantos nao sao uma distribuicao estatistica.

No L2 5/10 us, a V1 disparou em 4/4 trajetorias saudaveis. A revisao
V2, que altera somente a carga/descarga da confirmacao de 20/40 para
50/20 us, teve 0/4 alarmes saudaveis. Detectou tambem 2/2 casos de
cota antiga com carimbo recente e 2/2 de cota extrema. O viés extremo
foi detectado em 60.38 us; o replay em 2.0602 ms desde a partida,
incluindo a inibicao de 2 ms. A V2 ainda precisa dos cantos de
tolerancia, terceiro passo e demais falhas antes de ser escolhida.

Detectar e recuperar a logica sao problemas diferentes. Com cota
extrema no comum, habilitar a reserva mudou 47/68 para 43/68 acertos:
oito janelas recuperadas e doze novas falhas. No L2 5/10 saudavel,
comutacao desabilitada deu 55/68, V1 deu 43/68 e V2 deu 56/68.
Entre o controle desabilitado e V2 ocorreram onze recuperacoes e dez
regressoes. Sem disparo, ambos usam a mesma politica efetiva; alterar
o observador pode mudar os passos adaptativos. A diferenca de uma
janela nao prova melhora fisica causada pela V2.

Reduzir atraso/filtro de L2 de 20/50 para 5/10 us, com comutacao
desabilitada, mudou 51/68 para 55/68: dez recuperacoes e seis regressoes.
O residual RMS de Y caiu de 39.824 para 37.646 uA; D ficou em
23.806/23.748 uA. Frente ao comum nominal, L2 V2 reduziu o residual
de Y (44.544 -> 37.914 uA), mas aumentou o de D+E (19.061 ->
23.832 uA). A variacao total de g(x) permaneceu proxima: 1000.49/s
no comum e 1001.42/s em L2 V2. Nao ha reducao uniforme demonstrada
do esforco dinamico; essas medidas nao equivalem a estresse termico.

A convergencia numerica permanece aberta. O comum acertou 25, 23 e
28 de 34 janelas com passos 1.25, 0.625 e 0.3125 us; as duas
comparacoes sucessivas tiveram oito e onze discordancias. O L2 V1
com reserva deu 23, 20 e 25, com cinco e treze discordancias. Os
alarmes indevidos de L2 V1 persistiram no terceiro passo. L2 V2
acertou 30/34 e 26/34 nos dois passos, com oito discordancias.

As 64 trajetorias passaram no teto legado de 100.005 uA pelas tres
leituras. Os picos foram 90.022504 uA por tensao/shunt, 90.022613 uA
pelas correntes dos resistores e 90.804677 uA pelas sondas 0 V.
O maior pico da sonda coincide com um passo de 6.38e-16 s e shunts
quase constantes, sugerindo dificuldade numerica ainda nao isolada.
Nenhuma amostra foi removida. Nao foi demonstrado teto fisico estrito
de 90 uA. O comando de E respeitou 5 uA, mas seu pico fisico chegou
a 5.353212 uA. Esses limites sao de atuacao, nao consumo total da placa.

Prioridade do proximo lote: comparar concessao efetiva min(|pedido|,
cota), para nao reagir apenas a capacidade ociosa; confrontar essa
revisao e a V2 nos cantos de tolerancia e sob falhas; testar uma
reserva local com politica/filtro proximos aos nominais. Manter idade,
heartbeat e guarda global em paralelo. Isolar tambem a divergencia
das sondas e repetir o refinamento antes de prometer limites fisicos.
Sincronismo por mais de 0.85 s e retorno seguro apos reparo seguem
pendentes. Nenhum desses ensaios futuros foi contabilizado aqui.

Executadas 64 trajetorias completas novas (1088 janelas), com 56 da
matriz V1/controles/refinamento e oito da confirmacao V2. Comparacao
logica conferida tambem diretamente nos RAWs; plano e adendos preservados.

- [Relatorio completo](etapa18/ETAPA18_RESULTADOS.txt)
- [Comparacao visual](etapa18/comparacao_etapa18.svg)
- [Diagnostico da confirmacao](etapa18/diagnostico_confirmacao.svg)
- [Contrato para proximos modelos](etapa18/INTERFACE_PARA_PROXIMOS_MODELOS.txt)
- [Verificacao da entrega](etapa18/verificacao_entrega.json)
- [Errata da integracao de indicadores](etapa18/ERRATA_INTEGRACAO_INDICADORES.txt)
- [Correcao dos dados anteriores](etapa18/correcao_fracoes_anteriores.json)

Corrigido o helper compartilhado: integrar indicadores booleanos exige
conversao a float. Recalculadas 162 trajetorias unicas, corrigindo 184
registros das Etapas16/17 e a tabela impressa da Etapa16, com backups.
A referencia saudavel superava 91 uA em 62.15% do tempo (antes 31.12%).
Contagens de janelas, picos, alarmes, RMS e variacao total de g(x)
foram preservados.

Mantida a ressalva: 90 uA e cota de atuacao; controle/metadados ainda
comportamentais, 45 subpilares conceituais, nenhuma PCB ou chip especifico
validado. Os resultados desta matriz nao substituem a matriz 198/272 anterior.
