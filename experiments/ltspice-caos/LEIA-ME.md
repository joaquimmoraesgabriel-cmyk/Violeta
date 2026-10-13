# Primeiro experimento: circuito de Chua

1. No LTspice, use File > Open e abra `Chua.cir` nesta pasta. Se nao aparecer, selecione o filtro de todos os arquivos.
2. Escolha Simulate > Run (botao de executar). O arquivo e uma descricao textual do circuito; nao abre como desenho de componentes.
3. Na janela de graficos, clique com o botao direito e escolha Add Trace. Adicione `V(v1)` e `V(v2)` para ver as tensoes ao longo do tempo.
4. Para ver o atrator, deixe apenas `V(v2)` como curva. Clique com o botao direito nos numeros do eixo horizontal e altere Quantity para `V(v1)`. O grafico passa a mostrar V(v2) em funcao de V(v1). Em versoes que permitem a expressao no Add Trace, pode usar `V(v2) vs V(v1)`.

O resultado esperado e uma trajetoria que circula entre dois lobos: o atrator de dupla espiral. As tensoes se repetem aproximadamente, mas nao formam uma oscilacao periodica simples. Um grafico sozinho nao prova caos; e preciso analisar tambem a sensibilidade e a dinamica.

## Experimentos

- Mude `.param Rch=1770` para `2000`, execute e compare. Volte para `1770` depois. A resistencia altera a dinamica; diferentes valores podem gerar equilibrio, oscilacoes ou caos.
- Mude a condicao inicial de C1 de `IC=0.1` para `IC=0.100001`, execute e compare as curvas no tempo com a primeira execucao. Para uma comparacao confiavel, salve os resultados anteriores antes de executar novamente; reduza o passo maximo se quiser estudar a sensibilidade numericamente.
- O comando `.tran` simula 50 ms, omite os primeiros 5 ms do arquivo de resultados e limita o passo a 0,5 us. O `uic` usa as condicoes iniciais declaradas.

## Relacao com computacao por caos

Este exemplo mostra a dinamica caotica que pode servir de base para outros experimentos. Para realizar uma operacao computacional, ainda precisamos definir como uma entrada altera o circuito, como ler a saida e qual tarefa sera realizada. Ver um atrator caotico, por si so, nao constitui uma porta logica ou um computador.

O componente Bchua representa matematicamente o resistor nao linear e sua resistencia negativa. E um modelo ideal: um circuito fisico precisaria de um elemento ativo alimentado, por exemplo uma implementacao com amplificadores operacionais.

Referencia dos componentes e da curva nao linear: Chai Wah Wu, Introduction to Chaotic Phenomena in Chua's Circuit (1996): https://www.geocities.ws/chaiwahwu/chaosintro/chua_ckt.html

Arquivo preparado para LTspice; a simulacao ainda precisa ser executada para confirmar o comportamento nesta instalacao.
