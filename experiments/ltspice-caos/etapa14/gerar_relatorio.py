"""Relatorio com ablacões, bancada nao ideal e consistencia das medidas."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
S = json.loads((ROOT / 'resumo.json').read_text())
T = json.loads((ROOT / 'trajetorias.json').read_text())
B = json.loads((ROOT / 'bancadas_resultados.json').read_text())
A = json.loads((ROOT / 'auditoria_corrente.json').read_text())

def group(hardware, cap, detector, fault):
    return next(r for r in S if r['hardware'] == hardware and r['cap_operacao'] == cap and r['detector'] == detector and r['falha'] == fault)

names = ['Saudável', 'Parou e perdeu heartbeat', 'Atraso permanente de 500 µs', 'Inverteu o sinal', 'Parou com heartbeat mantido']
table = ['| Condição do topo | Sem reserva | Com reserva | Com reserva: passam nos dois passos |', '|---|---|---|---|']
for fault in range(5):
    a, b = group(0, 100e-6, 0, fault), group(0, 100e-6, 1, fault)
    table.append(f"| {names[fault]} | {a['corretas']}/68 | {b['corretas']}/68 | {b['corretas_ambos_passos']}/34 |")
physical = ['| Condição | Ideal com reserva, 90 µA | Circuito sem reserva, 90 µA | Circuito com reserva, 90 µA |', '|---|---|---|---|']
for fault in [0, 4]:
    groups = [group(0, 90e-6, 1, fault), group(1, 90e-6, 0, fault), group(1, 90e-6, 1, fault)]
    physical.append('| ' + names[fault] + ' | ' + ' | '.join(f"{r['corretas']}/34" for r in groups) + ' |')

bench = ['| Candidato de bancada | Maior pico das correntes salvas (µA) | Resultado no teto |', '|---|---|---|']
for prefix, label in [('BANCADA_limite', 'Realimentação simples'), ('BANCADA_intertravado', 'Com isolamento na partida'), ('BANCADA_antiwindup', 'Isolamento e redução de saturação ociosa')]:
    rs = [r for r in B if r['arquivo'] in [prefix, prefix + '_ref']]
    bench.append(f"| {label} | {max(r['pico_correntes_uA'] for r in rs):.3f} | {sum(r['fora_tolerancia'] for r in rs)}/{len(rs)} rejeitados |")
selected = [r for r in B if r['arquivo'].startswith('BANCADA_filtrado') and r['margem_limite'] == 90e-6 and r['gbw_limit'] == 100e6 and r['tau_cmd'] == 2e-6]
tolerance = [r for r in B if r['arquivo'] == 'BANCADA_tolerancias']
bench.append(f"| Candidato escolhido: 90 µA, resposta 100 MHz, RC 2 µs | {max(r['pico_correntes_uA'] for r in selected):.3f} | 2/2 passaram |")
bench.append(f"| Candidato com tolerâncias e offset | {max(r['pico_correntes_uA'] for r in tolerance):.3f} | 8/8 passaram |")
audit = ['| Repetição auditada | Reserva | Passo (µs) | Pico pelas tensões diretas (µA) | Pico das sondas (µA) |', '|---|---|---|---|---|']
for r in A:
    audit.append(f"| {r['arquivo']} / falha {r['falha_coord']} | {r['detector']} | {r['passo']*1e6:g} | {r['pico_tensoes_diretas_uA']:.6f} | {r['pico_sondas_uA']:.6f} |")

reserved = [t for t in T if t['detector'] == 1]
physical_reserved = [t for t in reserved if t['hardware'] == 1]
text = '''# Etapa 14: detectar a queda do topo e aproximar a atuação física

O detector por discrepância com memória e reserva recuperou os quatro defeitos do comando do topo no perfil AB exige mais. Com atuação ideal, a reserva passou em 340/340 janelas somando saudável, silêncio, atraso, inversão e silêncio com heartbeat. O resultado foi preservado nos dois passos máximos e estados iniciais testados, sem alarmes no período saudável. A integração com amplificadores genéricos ADI e shunts também recuperou o silêncio com heartbeat: 34/34 contra 31/34 sem reserva.

Isso valida uma recuperação neste conjunto de modelos e defeitos. Ainda não valida todos os perfis de carga, falhas internas do cálculo, a pirâmide completa, chips específicos ou uma PCB. A meta de placa virtual está registrada em PLANO_ETAPA14.md e orienta a separação entre estimativa, comando, medição e atuação.

## Escolha e funcionamento

O caminho de reserva calcula continuamente o vetor viável de correção a partir de A/B/C/D. A/B/C continuam somados em y; D atua em x. A medida pelo shunt é comparada com esse vetor viável, depois de filtros compatíveis. Isso evita tratar a diferença entre pedido bruto e corrente limitada como defeito do topo. O detector nunca lê a resposta AND correta nem a identidade ou o horário da falha.

```mermaid
flowchart LR
    E[Estimativas A B C D] --> L[Pedido local viável]
    L --> T[Comando do topo]
    L --> R[Caminho de reserva]
    T --> M[Seleção do comando]
    R --> M
    M --> P[Atuadores e limitador]
    P --> G[Porta MLC]
    P --> S[Resistores de medição]
    S --> D[Discrepância e confirmação RC]
    L --> D
    D --> H[Memória de alarme]
    H --> M
```

Medida e referência recebem filtro de 4 µs, com escala de 1 V para 100 µA. O limiar é 3 µA mais 10% da referência total em módulo, com referência mínima de 5 µA. A medida inclui offset de +0,5/-0,5 µA e duas senoides de ruído determinístico de 0,5 µA. Uma confirmação RC tem subida de 10 µs, descida de 20 µs e limiar 0,7. Após 2 ms iniciais, um alarme confirmado mantém a reserva ligada até o fim; não implementamos rearme automático.

O vetor local é a referência matemática favorável deste protótipo, disponível continuamente mesmo quando o comando do topo falha. A simulação não demonstra independência física de alimentação ou processamento entre topo, referência e reserva. Não injetamos falha comum nos sensores ou corrupção dessa referência. A reserva compartilha os dois atuadores; se um deles falhar, selecionar outro comando não o substitui.

## Comparação com atuação ideal

Mesmo limite nominal de 100 µA e parâmetros físicos da etapa 13, acrescentando shunts e diagnóstico iguais nas ablações. Falhas temporárias duram de 343,35 a 403,35 ms; o atraso de 500 µs é permanente. Cada célula tem dois estados iniciais e passos máximos de 2,5/1,25 µs, quatro trajetórias e 68 janelas. O resultado da mesma janela nos dois passos tem denominador 34.

''' + '\n'.join(table) + '''

A detecção das falhas temporárias ficou entre 12,58 e 12,62 µs. A reserva entra pouco depois, por causa da memória de confirmação. Para o atraso permanente, o primeiro alarme ocorreu de 2,067 a 2,071 ms após o começo: inclui os 2 ms de inibição inicial, não significa uma detecção de 2 ms após cada comando. Heartbeat é salvo para observação, mas não alimenta o detector. Assim ele consegue identificar ausência de atuação mesmo quando o heartbeat permanece.

As 20 trajetórias com reserva e 100 µA passaram em todas as 340 janelas e no critério baseado nas correntes salvas. A referência sem reserva acertou 313/340. Estas contagens são determinísticas e condicionadas à sequência, parâmetros e defeitos declarados; não estimam probabilidade de confiabilidade. Não testamos margens de estabilidade nem reestimamos Lyapunov em todas essas condições.

## Bancada do limitador não ideal

UniversalOpAmp2 é o modelo genérico fornecido pela Analog Devices, com ganho e resposta finitos, slew rate, limites de saída e saturação. O atuador usa shunt de 1 kΩ, alimentação ±5 V, ganho aberto 1e6, resposta de 2 MHz e slew de 10 V/µs. A medição diferencial, retificação de módulo e multiplicação por ganho ainda têm blocos comportamentais ideais; não apresentamos um circuito inteiro de chips já selecionados.

Uma bancada de 400 µs impôs comandos de 40+40 µA, depois 250+250 µA, inversão, liberação e novos comandos, sobre duas cargas de tensão senoidal. O teste do teto por realimentação não recebeu um limitador matemático final para esconder os picos. Patamar correto não bastou: os primeiros candidatos excederam o teto durante partida ou degrau, inclusive com passo de 5 ns e método Gear.

''' + '\n'.join(bench) + '''

O candidato escolhido isola a saída durante a partida por chave controlada por RC (100 kΩ/100 pF e limiar 3 V), evita saturar negativamente o amplificador de limite sem necessidade e filtra o comando com RC de 2 µs antes da realimentação comum. O patamar operacional de proteção é 90 µA, preservando margem para transientes abaixo do teto nominal de 100 µA. A resposta de 100 MHz é uma hipótese exigente do amplificador genérico, ainda sem escolha de chip, custo ou consumo.

Os oito testes de tolerância combinaram shunts ±1%, offset do atuador ±100 µV e resposta do atuador de 1/2 MHz, em passo de 5 ns/Gear. São limites escolhidos para o ensaio, não tolerâncias de peças selecionadas. Uma configuração de 95 µA com resposta de 100 MHz e RC de 2 µs chegou a cerca de 101,87 µA e foi rejeitada. Outras configurações de 95 µA passaram no conjunto nominal, mas deixaram menos margem para a realização física.

As chaves ainda usam modelo ideal de comutação sem capacitância de desligamento ou injeção de carga. Fontes de alimentação são ideais. Esses efeitos, ruído real dos componentes, tolerâncias do temporizador, retorno de corrente, parasitas de trilhas e comportamento térmico ainda precisam entrar na validação. Corrente de atuação não é consumo total da placa.

## Integração com a porta

A integração usa o candidato de 90 µA e compara com uma referência ideal também de 90 µA. Há oito trajetórias com amplificadores, em passo máximo de 1,25 µs, dois estados iniciais, topo saudável ou silêncio com heartbeat; quatro referências ideais adicionais isolam o custo da margem. O filtro de referência do detector inclui os 2 µs conhecidos do comando. A inicialização da saída usa o temporizador RC da bancada.

''' + '\n'.join(physical) + f'''

Com reserva, a integração passou em 68/68 janelas entre as duas condições, sem alarmes no período saudável. A detecção do silêncio levou de {group(1,90e-6,1,4)['latencia_min_us']:.3f} a {group(1,90e-6,1,4)['latencia_max_us']:.3f} µs. O maior pico das correntes salvas entre todas as oito trajetórias integradas foi {max(t['pico_correntes_uA'] for t in T if t['hardware']==1):.6f} µA, abaixo do critério de 100,005 µA. A integração não repetiu ainda dois passos de tempo, nem os outros perfis, atraso e inversão com os amplificadores. A robustez da bancada não substitui esses testes conjuntos.

## Consistência da verificação de corrente

Quatro execuções da referência ideal sem reserva e com atraso acusaram ultrapassagem pelo registro das sondas, chegando a 100,636 µA. A auditoria repetiu duas delas com x inicial=-0,37 nos dois passos, junto com duas repetições com reserva. A corrente calculada diretamente como queda de tensão sobre o resistor dividida por 1 kΩ ficou em cerca de 100,000143 µA; as fontes e os próprios resistores salvos ficaram em cerca de 100,000004 µA. Esses métodos não confirmaram o excesso das sondas nas repetições auditadas.

''' + '\n'.join(audit) + '''

Na auditoria do circuito integrado, as tensões diretas dos shunts e as medidas de pico permaneceram abaixo do teto. A diferença pontual entre sondas e tensões ainda pode ser maior que a diferença entre seus picos. Não identificamos aqui o mecanismo interno do simulador responsável por toda essa discordância. Não atribuímos a ela um excesso físico confirmado. Os sinalizadores originais de corrente das sondas foram preservados no CSV/JSON; eles não constituem sozinhos a conclusão final de capacidade quando os métodos discordam.

RAW armazena tensões e correntes em 32 bits. Subtrair tensões próximas e dividir pelo shunt produz pequenos resíduos de armazenamento; o critério de 0,005 µA acima dos 100 µA foi mantido. Para etapas futuras, salvar sempre as tensões diretas do shunt, as correntes dos resistores e fontes e as sondas, além de conferir a consistência. Não reinterpretamos automaticamente as execuções históricas que não possuem esses sinais.

## O que foi alcançado e o que falta

A queda do comando do topo deixou de causar falha lógica nos casos avaliados quando o detector e a reserva estavam ativos. A parada com heartbeat mantido, antes invisível ao diagnóstico, passou a ser detectada pela atuação ausente. Também encontramos e reduzimos transientes que não existiam no modelo de limitador ideal.

Ainda faltam modelos de chips específicos para o bloco de medida e limitador, estabilidade de malhas, alimentação e partida não ideais, parasitas das chaves, falhas da medição/limitador/reserva, falha do próprio atuador, rearme e casos novos de carga/sensores. O modelo atual de reserva não é uma proteção contra toda falha comum. A pirâmide de 36 sensores adaptativos continua sem integração.

Para a Etapa 15, a prioridade é repetir a integração em passo menor e casos novos e escolher uma realização concreta do atuador/medição/limitador com modelos de componentes. Verificar saturação, estabilidade, partida e capacitância de desligamento das chaves antes de transferir para layout. Depois, extrair R/L/C e acoplamentos do layout e associar simulação elétrica, alimentação e modelos térmicos. Uma PCB virtual exige esses modelos; desenhar a placa por si só não os inclui.

Referências de base: [ADI, resistor de medição e limitação de saída](https://wiki.analog.com/university/courses/electronics/text/chapter-16) e [ADI, modelos térmicos no LTspice](https://wiki.analog.com/resources/quick-start/power-op-amp-thermal-model). Os controladores, falhas e resultados numéricos descritos são novos deste projeto.

## Evidências e reprodução

52 trajetórias principais e 884 janelas, 60 trajetórias curtas de bancada e seis auditorias adicionais com 102 janelas analisadas separadamente. As 38 trajetórias de bancada que falharam foram preservadas. Modelos, manifestos, logs e RAW estão nesta pasta; resultados.csv, trajetorias.json, resumo.json, bancadas_resultados.json, candidato_limitador.json e auditoria_corrente.json registram as evidências.

Preparadores de bancada: preparar_bancada.py, preparar_intertravamento.py, preparar_antiwindup.py e preparar_filtro_comando.py. preparar_integracao.py cria o modelo escolhido e os casos com circuito; preparar_tolerancias.py cria sua extensão. preparar_etapa14.py gera a comparação do detector, e preparar_auditoria_corrente.py cria as repetições de consistência. Executar os três manifestos com executar.ps1; as bancadas são arquivos BANCADA_*.cir individuais. analisar_bancadas.py, analisar_etapa14.py lotes_detector.json lotes_circuito.json, analisar_auditoria.py e gerar_relatorio.py validam e produzem os resultados.

Para inspecionar no LTspice: PHY_d1_falha4.cir (com reserva) e PHY_d0_falha4.cir (sem reserva). Selecionar uma condição inicial por vez e adicionar V(saida), V(referencia), V(ler). Em outro painel, V(reserva_ativa), V(discrepancia), V(limiar) e V(heartbeat). V(orcamento) é monitor; para a capacidade, consultar também as correntes e tensões diretas descritas acima.
'''
(ROOT / 'ETAPA14_RESULTADOS.md').write_text(text, encoding='utf-8')
print('Relatorio final salvo: 52 trajetorias principais, 60 bancadas e 6 auditorias.')
