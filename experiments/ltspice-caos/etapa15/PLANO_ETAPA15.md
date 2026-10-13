# Etapa 15 — extensão da integração não ideal

Plano definido antes das simulações. Manter os modelos e parâmetros da Etapa 14: dois atuadores genéricos, shunts de 1 kΩ, limitador com alvo de 90 µA, filtro de comando de 2 µs, detector por discrepância e reserva retida. O teto de aceitação é 100,005 µA. Não reajustar o detector em função dos resultados deste lote.

## Matriz principal

64 trajetórias de 0,85 s, 17 janelas por trajetória: 1.088 janelas. Condições iniciais x=±0,37 e y=-0,2.

- Reserva ligada: saudável e silêncio com heartbeat presente nos quatro perfis (equilibrado, AB, CD, alta demanda), nos passos máximos 1,25 e 0,625 µs: 32 trajetórias.
- Reserva ligada: atraso permanente de 500 µs e inversão temporária em AB e alta demanda, nos dois passos: 16 trajetórias.
- Reserva ligada: parada sem heartbeat em AB, nos dois passos: quatro trajetórias.
- Referência sem reserva: silêncio, atraso e inversão em AB e alta demanda, em 1,25 µs: 12 trajetórias.

Silêncio, parada e inversão de 343,35 a 403,35 ms; atraso desde o início. São falhas no comando do topo. O cálculo local e a alimentação continuam disponíveis. O detector não recebe o código de falha, o instante de injeção nem a resposta lógica correta.

## Critérios

Uma janela passa somente se todos os valores de x no intervalo de leitura (30–49 ms de cada bloco de 50 ms) tiverem o sinal AND correto. Comparar janelas correspondentes nos dois passos; concordância de classificação não prova convergência ponto a ponto de trajetórias caóticas. Não somar repetições como se fossem amostras aleatórias independentes.

Medir corrente pela diferença direta de tensões nos dois shunts dividida por 1 kΩ. Salvar também correntes dos resistores, sondas de 0 V e medidas comportamentais; relatar diferenças e preservar qualquer excesso indicado. Verificar partida e toda a trajetória. O orçamento é corrente de atuação, não consumo de alimentação.

Registrar alarmes anteriores à falha, alarmes saudáveis, latência, retenção da reserva, margem lógica e janelas que falham mesmo após diagnóstico. Tratar saturação legítima e insuficiência de capacidade separadamente de falha do topo.

## Decisão ao terminar

Controle complementar definido durante a execução, antes da leitura dos resultados de alta demanda: oito trajetórias adicionais saudáveis no perfil de alta demanda, com atuadores ideais e o mesmo RC de comando de 2 µs, partida, detector e shunts; capacidades de 90 e 100 µA, dois passos e dois estados iniciais. A comparação de 90 µA com o circuito não ideal separa o conjunto atuador/limitador da restrição de capacidade. A comparação 90/100 µA mantém a atuação ideal e muda a capacidade disponível. Esses controles são reportados separadamente das 64 trajetórias principais; não aprovam proteção física idealizada.

Se a alta demanda falhar mesmo com topo saudável, investigar primeiro a capacidade e a margem lógica. Se houver alarmes saudáveis, investigar a referência e a resposta dos atuadores antes de trocar limiares. Se o teto de corrente falhar, suspender a aprovação do candidato. Só avançar a componentes específicos a partir de requisitos medidos; esta etapa não aprova uma placa física.

Permanecem as limitações da Etapa 14: sensores favoráveis compartilhados, cálculo local comportamental, guardas ideais de sinal/capacidade, medição e multiplicação ideais, amplificadores genéricos, alimentação ideal e chave sem parasitas. O limitador isolado já foi exigido além da capacidade na bancada anterior; o lote integrado atual ainda conserva a guarda de comando. Modelar chips, estabilidade, alimentação, chave real e térmica continua necessário para a futura placa virtual.

## Seguimento motivado pelos resultados

A matriz inicial e os controles mostraram alarmes indevidos em alta demanda saudável, inclusive com atuação ideal. Quatro repetições instrumentadas (circuito/ideal de 90 µA, x=-0,37 e dois passos) salvaram os nós dos filtros. A auditoria encontrou a carga do segundo RC sobre o primeiro na referência; no caminho de atuação/medição, eles estavam isolados. Os limiares permaneceram inalterados.

A correção isola os RCs da referência com seguidores ideais. A regressão inclui 24 trajetórias com circuito (AB saudável/silencioso e alta demanda saudável/silenciosa/atrasada/invertida, dois passos e dois estados iniciais), mais quatro com atuação ideal de 90 µA em alta demanda saudável. Assim, a etapa compreende 104 trajetórias válidas quando todos esses conjuntos estão completos: 64 originais, oito controles, quatro auditorias e 28 de regressão. Resultados e falhas de cada conjunto permanecem separados; a regressão não substitui silenciosamente a matriz original.
