# Etapa 15 — extensão dos atuadores não ideais

## Conclusão da etapa e versão candidata

A Etapa 15 identificou e corrigiu uma assimetria entre os filtros da referência e da medição. A referência tinha RCs em cascata sem isolamento; o segundo carregava o primeiro. A auditoria reproduziu um alarme com atuador ideal: a corrente seguia o comando filtrado em -2,459593 µA, mas o primeiro filtro da referência marcava -5,138084 µA, com comandos de entrada praticamente iguais. Não era necessário aumentar os limiares do detector.

A correção acrescentou seguidores ideais entre os RCs da referência. Na regressão de 28 trajetórias: 0 alarmes indevidos; pico pelos shunts 90.017140 µA; 0 violações do teto de 100,005 µA. Com atuação não ideal, AB saudável/silencioso acertou 136/136; alta demanda saudável/silenciosa/atrasada/invertida, 198/272. O controle ideal de 90 µA após a correção acertou 53/68.

O candidato para continuar é `MLC_filtros_isolados.inc`. Esta regressão não repete toda a matriz original: cobre AB saudável/silencioso, quatro condições de alta demanda e um controle ideal. Os resultados anteriores à correção permanecem nas tabelas abaixo. Corrigir os alarmes não equivale a resolver a lógica em alta demanda.

Detalhes: [correção e regressão dos filtros](CORRECAO_FILTROS.md), [controle de capacidade](CONTROLE_CAPACIDADE.md). Foram concluídas 104 trajetórias válidas (1.768 janelas): 64 da matriz inicial, oito controles, quatro auditorias e 28 da correção. Não são 104 condições independentes; incluem repetições e comparações pareadas.

## Decisão para o próximo lote

Manter o alvo de 90 µA e a referência corrigida. Investigar primeiro a margem lógica em alta demanda: separar atraso/erro das estimativas da restrição de capacidade, variar a intensidade das perturbações e repetir os casos críticos com passo menor. Os controles de atuação ideal sem a correção dos filtros deram 50/68 a 90 µA e 56/68 a 100 µA; usar toda a capacidade nominal não eliminou as falhas. Qualquer nova estratégia deve preservar o teto e ser comparada com a versão corrigida sob as mesmas condições.

Depois, substituir os seguidores, a medida e os atuadores por circuitos de componentes específicos, verificando largura de banda, offset, faixa de tensão, estabilidade e alimentação. A correção introduziu um seguidor ideal; sua implementação real ainda exige caracterização. Só então incluir interconexões e térmica na placa virtual.

64 trajetórias completas de 0,85 s, 1.088 janelas lógicas. O circuito e seus parâmetros foram preservados da Etapa 14. Foram ampliados os perfis e falhas e reduzido o passo máximo de 1,25 para 0,625 µs. As contagens são resultados determinísticos desta matriz; não estimativas estatísticas de confiabilidade.

## Matriz original antes da correção — resultado com reserva

| Perfil | Comando do topo | Acertos em 1,25 µs | Acertos em 0,625 µs | Corretas nos dois passos | Classificações diferentes |
|---|---|---:|---:|---:|---:|
| Equilibrado | Saudável | 34/34 | 34/34 | 34/34 | 0 |
| Equilibrado | Silêncio com heartbeat | 34/34 | 34/34 | 34/34 | 0 |
| AB | Saudável | 34/34 | 34/34 | 34/34 | 0 |
| AB | Parada sem heartbeat | 34/34 | 34/34 | 34/34 | 0 |
| AB | Atraso de 500 µs | 34/34 | 34/34 | 34/34 | 0 |
| AB | Inversão | 34/34 | 34/34 | 34/34 | 0 |
| AB | Silêncio com heartbeat | 34/34 | 34/34 | 34/34 | 0 |
| CD | Saudável | 34/34 | 34/34 | 34/34 | 0 |
| CD | Silêncio com heartbeat | 34/34 | 34/34 | 34/34 | 0 |
| Alta demanda | Saudável | 26/34 | 21/34 | 16/34 | 15 |
| Alta demanda | Atraso de 500 µs | 24/34 | 20/34 | 17/34 | 10 |
| Alta demanda | Inversão | 27/34 | 25/34 | 20/34 | 12 |
| Alta demanda | Silêncio com heartbeat | 25/34 | 25/34 | 19/34 | 12 |

Com reserva: 805/884 janelas, 36/52 trajetórias inteiramente corretas. Nos testes saudáveis: 251/272 janelas. Alarmes anteriores à falha ou em condição saudável: 3 de 52 trajetórias protegidas.

## Comparação pareada com a reserva desligada

Esta comparação usa somente 1,25 µs e os mesmos dois estados iniciais. Os resultados do passo menor não são misturados à referência.

| Perfil | Falha | Sem reserva | Com reserva | Janelas recuperadas | Janelas que pioraram |
|---|---|---:|---:|---:|---:|
| AB | Silêncio com heartbeat | 31/34 | 34/34 | 3 | 0 |
| AB | Atraso de 500 µs | 29/34 | 34/34 | 5 | 0 |
| AB | Inversão | 31/34 | 34/34 | 3 | 0 |
| Alta demanda | Silêncio com heartbeat | 22/34 | 25/34 | 9 | 6 |
| Alta demanda | Atraso de 500 µs | 16/34 | 24/34 | 10 | 2 |
| Alta demanda | Inversão | 21/34 | 27/34 | 7 | 1 |

## Corrente e consistência da medição

A corrente principal é calculada externamente como a soma dos módulos das quedas de tensão diretamente nos dois shunts, divididas por 1 kΩ. Foram salvas também correntes dos resistores, sondas de 0 V e monitores comportamentais. O critério permanece 100,005 µA, incluindo partida e transientes; 90 µA é o alvo operacional.

| Método | Maior pico no lote (µA) | Trajetórias acima de 100,005 µA |
|---|---:|---:|
| Tensões diretas nos shunts | 90.015769 | 0 |
| Correntes dos resistores | 90.015730 | 0 |
| Sondas de 0 V | 90.091038 | 0 |

Maior diferença pontual entre soma por tensões e soma por resistores: 0.000237 µA; entre tensões e sondas: 0.953675 µA; entre tensões e monitores: 0.000237 µA. Essas diferenças pontuais não são a diferença entre os picos. Os valores em RAW usam armazenamento de 32 bits. Um excesso indicado por apenas um método deve ser auditado; nenhuma linha original é apagada.

## Detecção

| Perfil | Falha | Primeiro alarme: mínimo–máximo (µs) |
|---|---|---:|
| Equilibrado | Silêncio com heartbeat | 14.354–14.443 |
| AB | Parada sem heartbeat | 13.865–13.913 |
| AB | Atraso de 500 µs | 2090.904–2092.176 |
| AB | Inversão | 13.865–13.913 |
| AB | Silêncio com heartbeat | 13.865–13.913 |
| CD | Silêncio com heartbeat | 14.017–14.165 |
| Alta demanda | Atraso de 500 µs | 2012.037–2012.038 |
| Alta demanda | Inversão | 13.999–14.000 |
| Alta demanda | Silêncio com heartbeat | 13.999–14.000 |

Para as falhas temporárias, o intervalo acima é medido a partir de 343,35 ms. Para o atraso permanente, é o instante desde o início, incluindo a inibição inicial de 2 ms; não equivale à latência de cada mudança de comando. Alarme não significa recuperação lógica. O estado de reserva permanece retido e não há rearme automático.

## Janelas que falharam com reserva

| Arquivo | Caso | Passo (µs) | x inicial | Janelas (índice 0–16) | Menor margem de x (V) |
|---|---:|---:|---:|---|---:|
| EXP_p3_f0_d1 | 0 | 1.25 | -0.37 | 9, 10, 13, 15 | -1.38283 |
| EXP_p3_f0_d1 | 1 | 1.25 | 0.37 | 4, 8, 14, 15 | -1.31911 |
| EXP_p3_f0_d1 | 2 | 0.625 | -0.37 | 4, 6, 9, 11, 15 | -1.34767 |
| EXP_p3_f0_d1 | 3 | 0.625 | 0.37 | 2, 6, 7, 9, 10, 11, 13, 14 | -1.37639 |
| EXP_p3_f4_d1 | 0 | 1.25 | -0.37 | 9, 11, 13 | -1.35733 |
| EXP_p3_f4_d1 | 1 | 1.25 | 0.37 | 4, 9, 10, 11, 13, 15 | -1.38473 |
| EXP_p3_f4_d1 | 2 | 0.625 | -0.37 | 4, 6, 9, 10, 13 | -1.38404 |
| EXP_p3_f4_d1 | 3 | 0.625 | 0.37 | 2, 6, 10, 14 | -1.33256 |
| EXP_p3_f2_d1 | 0 | 1.25 | -0.37 | 4, 6, 9, 15 | -0.112814 |
| EXP_p3_f2_d1 | 1 | 1.25 | 0.37 | 4, 9, 10, 12, 13, 14 | -1.3489 |
| EXP_p3_f2_d1 | 2 | 0.625 | -0.37 | 2, 4, 6, 7, 8, 9, 11, 13, 14 | -1.37971 |
| EXP_p3_f2_d1 | 3 | 0.625 | 0.37 | 6, 9, 12, 13, 14 | -1.38087 |
| EXP_p3_f3_d1 | 0 | 1.25 | -0.37 | 10 | -0.109545 |
| EXP_p3_f3_d1 | 1 | 1.25 | 0.37 | 4, 7, 9, 13, 14, 15 | -1.37937 |
| EXP_p3_f3_d1 | 2 | 0.625 | -0.37 | 4, 6, 9, 10, 13 | -1.33335 |
| EXP_p3_f3_d1 | 3 | 0.625 | 0.37 | 2, 6, 11, 15 | -1.39068 |

Cada janela corresponde ao bloco de 50 ms indicado pelo índice, com leitura de 30 a 49 ms dentro do bloco. Um único valor com sinal errado reprova a janela. O CSV preserva a margem de cada janela, inclusive quando os passos discordam.

## Alcance da evidência e placa virtual

A falha é aplicada ao comando do topo. O cálculo local, a alimentação e os sensores permanecem disponíveis. A reserva compartilha sensores e atuadores e não representa redundância física completa. As guardas ideais de sinal e capacidade continuam antes da atuação; a inversão pode ser bloqueada por essa guarda. Portanto, o ensaio não atribui toda proteção ao limitador não ideal.

Os amplificadores são UniversalOpAmp2 genéricos. Medição diferencial, soma de módulos, multiplicação, cálculo local, alimentação e chave ainda têm idealizações. O lote não inclui chips selecionados, térmica, acoplamentos de trilhas, ruído estatístico, falha da reserva ou do próprio atuador. A pirâmide completa de sensores adaptativos não foi integrada.

A concordância entre duas classificações lógicas não demonstra convergência ponto a ponto. Falhas e divergências devem guiar o próximo experimento. A passagem à placa virtual dependerá da realização dos blocos, análise de estabilidade e alimentação, tolerâncias e modelos de interconexão e térmica.

## Evidências e reprodução

preparar_etapa15.py gera a matriz; executar.ps1 executa os decks listados em lotes.json (Slot/Slots distribuem decks entre processos). analisar_etapa15.py valida logs e RAW completos e produz trajetorias.json, resultados.csv e resumo.json; gerar_relatorio.py produz este documento e comparacoes.json. Os RAW e logs permanecem junto dos circuitos.

Modelos copiados sem alteração da Etapa 14 (SHA-256):

- MLC_circuito_reserva.inc: `4c5244fe9a1a79794437634806f32d191153835104b75434f39ad2a09f9527e1`
- atuadores_etapa14.inc: `7cdf113eab89fa5a4dc425bf58dd3e8eeca36485eed89098c9eea2e9e9698cb4`
- UniversalOpAmp2.lib: `68ca9f57957c7006e09f9a5349a0823fa93e9e1f2618a6fc0d2ebc7a83b1271e`

## Auditoria e alterações posteriores à matriz inicial

As quatro repetições AUD_circuito/AUD_ideal90 salvaram os filtros internos. auditoria_diagnostico.json e AUD_*_caso*_evento.csv registram a diferença de caminho. Os preparadores inicialmente emitiram uma varredura de um único ponto, rejeitada pelo LTspice antes de simular. O formato foi corrigido para dois passos; os dois logs *.erro_preparacao.log foram preservados e não entram na contagem de trajetórias válidas.

preparar_correcao_filtros.py gera a correção e as 28 trajetórias; executar.ps1 com lotes_filtros.json as executa; analisar_correcao.py compara os resultados. analisar_auditoria.py gera o diagnóstico das quatro repetições. gerar_fechamento.py consolida os quatro conjuntos após suas análises. O modelo original da Etapa 14 não foi sobrescrito.
