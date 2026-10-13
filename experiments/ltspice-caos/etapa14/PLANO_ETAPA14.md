# Etapa 14: detecção, reserva e aproximação da atuação física

A meta futura registrada pelo usuário é migrar o circuito validado para uma placa virtual antes de fabricar. A escolha desta etapa é construir interfaces mensuráveis e caracterizar a proteção de corrente e a recuperação da falha do topo separadamente. A simulação completa com componentes, parasitas de layout, alimentação, ruído e modelo térmico é uma sequência de validações; passar no modelo comportamental atual não equivale a passar nessa sequência.

## Hipóteses e critérios definidos antes das contagens

O detector compara o pedido local viável com a atuação medida por resistor shunt. Usa os mesmos sensores A/B/C/D e os mesmos erros do ensaio anterior; não usa a resposta AND correta, o código de falha nem o horário de sua injeção. Pedido viável significa pedido já compatível com a capacidade de atuação, portanto a saturação legítima não deve ser confundida com um topo parado.

Medida e referência recebem filtros RC de 4 µs. As correntes são escaladas para 1 V por 100 µA. A divergência exige erro absoluto maior que 3 µA mais 10% do módulo da referência, e referência total superior a 5 µA. Há offset de +0,5/-0,5 µA e ruído senoidal determinístico de 0,5 µA em 13.007/17.011 Hz na medida. Esses sinais não constituem distribuição estatística de ruído real. O detector só está habilitado após 2 ms de acomodação inicial.

Uma confirmação RC com constante de subida de 10 µs, descida de 20 µs e limiar 0,7 aciona a memória. A constante não é uma promessa de latência exata. A memória mantém a reserva até o fim da execução; rearme automático não é testado. A reserva recalcula a corrente atual por um caminho local independente do comando do topo, mas compartilha os sensores e atuadores. Não corrige automaticamente a falha desses elementos ou sua própria falha.

44 trajetórias principais: com e sem reserva, topo saudável, silêncio, atraso permanente de 500 µs, inversão de sinal e silêncio com heartbeat presente; dois estados iniciais e passos máximos 2,5/1,25 µs. Quatro dessas trajetórias avaliam uma reserva com orçamento operacional de 90 µA, separando o efeito de uma margem de proteção. A capacidade nominal total permanece 100 µA. São 748 janelas lógicas.

Atualização após a bancada: oito trajetórias adicionais integraram o candidato não ideal de 90 µA, resposta do limitador de 100 MHz e RC de comando de 2 µs, com e sem reserva, topo saudável ou silêncio com heartbeat mantido, em passo máximo de 1,25 µs. O conjunto principal final tem 52 trajetórias e 884 janelas; a bancada e as auditorias são contadas separadamente no relatório final.

Registrar janelas e trajetórias corretas, classificações que mudam com passo, pico das correntes somadas externamente, tempo até alarme/reserva, ativação sem falha e permanência na reserva. Critério numérico da atuação: pico inferior ou igual a 100,005 µA, preservado da etapa 13. Uma divergência detectada não garante recuperação lógica.

## Limitador e bancada separada

O modelo UniversalOpAmp2 fornecido pela Analog Devices inclui ganho e largura de banda finitos, slew rate, alimentação, saturação e limite de corrente de saída. Usamos shunts de 1 kΩ, alimentação de ±5 V e um amplificador por atuador. A soma dos módulos das medidas controla o ganho comum. O amplificador genérico, os blocos de medida diferencial, retificação e multiplicação não constituem uma escolha de chips nem um esquema integralmente realizável já aprovado.

Bancada de 400 µs: comandos de baixa demanda, degrau para 250+250 µA, reversão de sinal, liberação e novos comandos; duas cargas com tensão oscilante. Varrer patamar de proteção de 90/95 µA e largura de banda do limitador de 20/100/200 MHz. Repetir com passo menor e outro método de integração quando houver excesso, sem alterar o limite aceito. Conferir a corrente nos portos da carga fora do SPICE. Preservar os circuitos e resultados que falham.

Partida, patamar e transientes são critérios distintos. Um limitador que acerta o patamar, mas ultrapassa o teto durante partida/degrau, falha no requisito de pico. Isolamento de saída controlado por RC e prevenção de saturação desnecessária do controlador são candidatos a testar. Uma proteção ideal adicional não será usada para ocultar os picos da bancada física.

## Caminho para a placa virtual

1. Substituir gradualmente os blocos ideais por circuitos e macromodelos de componentes específicos; medir margem e estabilidade de cada malha.
2. Escolher alimentação, escala de tensões e correntes, resistores de medição, faixa de modo comum, compensação, partida e proteção de saída.
3. Inserir tolerâncias, offsets, limites de tensão/corrente, ruído e dependência de temperatura adequados aos componentes escolhidos.
4. Acrescentar resistência, indutância, capacitância e acoplamento extraídos de uma proposta de layout; simular retorno de corrente e integridade da alimentação.
5. Usar os modelos térmicos e de interconexão adequados, associados à simulação elétrica. Um editor de PCB, por si só, não representa todos esses efeitos.

Referências técnicas: [ADI, técnicas de limitação com resistor de medição](https://wiki.analog.com/university/courses/electronics/text/chapter-16) e [ADI, modelos térmicos de amplificadores no LTspice](https://wiki.analog.com/resources/quick-start/power-op-amp-thermal-model). Os valores e o controlador desta etapa são hipóteses novas deste projeto, não resultados dessas fontes.
