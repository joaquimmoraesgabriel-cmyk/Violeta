from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
s=json.loads((ROOT/'resumo.json').read_text())
rows=list(csv.DictReader((ROOT/'resultados.csv').open(encoding='utf-8-sig')))
table=[]
for step in [2.5e-6,1.25e-6,.625e-6]:
    rs=[next(r for r in s if r['perfil']==2 and r['topologia']==top and r['passo']==step and r['arquivo']!='MLC_D_demo') for top in [0,8]]
    table.append(f"| {step*1e6:g} | {rs[0]['corretas']}/34 | {rs[0]['menor_margem']:.6f} | {rs[1]['corretas']}/34 | {rs[1]['menor_margem']:.6f} |")
combined=[]
for step in [2.5e-6,1.25e-6,.625e-6]:
    rs=[next(r for r in s if r['perfil']==1 and r['topologia']==top and r['passo']==step) for top in [7,15]]
    combined.append(f"| {step*1e6:g} | {rs[0]['corretas']}/34 | {rs[0]['menor_margem']:.6f} | {rs[1]['corretas']}/34 | {rs[1]['menor_margem']:.6f} |")
peak=max(r['pico_orcamento_uA'] for r in s)
text=f'''# Etapa 11: um problema concreto para o pilar D

D compensa uma deriva multiplicativa na curva nao linear g(x), atuando no estado x. A, B e C corrigem termos do estado y (amortecimento, bias e amplitude de excitacao); esta e uma funcao distinta. No desvio isolado de +/-1%, D manteve 34/34 janelas nos passos maximos de 2,5, 1,25 e 0,625 us. Sem D, houve falhas em todos esses passos. Isso justifica estudar o canal D no modelo, sem demonstrar a necessidade de nove pilares.

## Base e hipotese nova

O modelo MLC de referencia contem xdot=y-g(x), ydot=-a*y-x+b+I+f(t), com g por trechos. A fonte original apresenta as equacoes e uma realizacao com elemento nao linear: [Murali et al., Chaotic Attractor Hopping yields Logic Operations](https://arxiv.org/pdf/1811.10029). A deriva, o sensor de D e a compensacao abaixo sao hipoteses deste estudo, nao resultados atribuidos ao artigo.

Introduzimos xdot=y-(1+d(t))*g(x). D mede uma replica d_est, espera 50 us, filtra com resposta de 100 us e solicita corrente proporcional a d_est*g(x) no capacitor que representa x. Essa corrente cancela idealmente o termo extra -d*g(x), mas o cancelamento e imperfeito com erro, atraso e limitacao de corrente.

g(x) tem inclinacoes nominalmente -1,02 na regiao interna e -0,55 na externa, com quebras em +/-1. Multiplicar a curva inteira altera ambas proporcionalmente. Nao modelamos mudanca independente das duas inclinacoes, quebra deslocada, histerese, saturacao de amplificadores ou temperatura real. Uma montagem fisica precisa de um circuito para medir esse desvio e de um atuador capaz de compensar a caracteristica; nao basta assumir a replica conhecida.

## Sensor, perturbação e capacidade

Desvio D senoidal a 211 Hz, fase 17 graus, amplitude relativa 0,004 (0,4%) ou 0,010 (1%). Sensor ideal de parametro com offset +0,00002, latencia 50 us, filtro 100 us. Os outros sensores conservam os erros das etapas anteriores. As fontes comportamentais representam correntes nos dois sentidos, e os canais ativos compartilham capacidade nominal de 100 uA pela regra proporcional. Correntes em x e em y sao somadas em modulo para impedir cancelamento aparente de recursos.

A quantidade de corrente nao e um consumo de energia. O sensor D ainda conhece uma replica favoravel do parametro; nao e estimado pela saida AND desejada. A amplitude relativa de 1% e uma escolha do ensaio, nao uma tolerancia medida de componentes.

## Desvio isolado forte

Cada celula tem 34 janelas, x inicial=-0,37/+0,37, y=-0,2. Apenas D e perturbado. Os demais canais estao desligados nesta comparacao.

| Passo maximo (us) | Sem correcao | Menor margem | Somente D | Menor margem |
|---|---|---|---|---|
'''+ '\n'.join(table)+'''

No desvio isolado menor, +/-0,4%, sem D e com D passaram em 34/34 nos passos 2,5 e 1,25 us. D melhorou a menor margem de cerca de 0,227 para 0,27, mas nao foi necessario para acertar esse conjunto. Assim, sua necessidade depende da faixa de desvio e do requisito de margem.

## Quatro desvios e retirada de D

Amortecimento +/-0,25% a 500 Hz; bias +/-0,003 a 137 Hz, fase 40; excitacao +/-0,002 a 73 Hz, fase 65; curva nao linear +/-0,4% a 211 Hz, fase 17. Mesma capacidade nominal de 100 uA, sem reservar corrente para canais desligados.

| Passo maximo (us) | A+B+C | Menor margem | A+B+C+D | Menor margem |
|---|---|---|---|---|
'''+ '\n'.join(combined)+f'''

Em 2,5 us, acrescentar D piorou a contagem de 34 para 33. Em 1,25 e 0,625 us, ambos passaram e a margem favoreceu D. A execucao conjunta e sensivel ao passo e a alocacao modifica as correntes de outros canais. Nao atribuimos a falha exclusivamente a escassez de corrente ou ao erro numerico: ainda nao isolamos essas causas. Este resultado motiva comparar regras de coordenacao, sem selecionar apenas o passo favoravel.

## Leitura e precisao

17 blocos de entrada de 50 ms, cobrindo as 16 transicoes entre 00/01/10/11 sem reiniciar o circuito. Avaliamos os extremos de x de 30 a 49 ms de cada bloco. Para AND, 11 exige x>0; os demais x<0. Uma passagem para o lado errado dentro dessa janela conta como falha. Sao trajetorias deterministas e extremos de uma solucao numerica finita, nao probabilidades de confiabilidade nem provas continuas.

24 trajetorias iniciais, 8 de refinamento motivado pela sensibilidade conjunta e 2 de demonstracao: {len(rows)} janelas. Tolerancias reltol=1e-6, vntol=1e-9, abstol=1e-12. Maior pico registrado {peak:.9f} uA, com tolerancia de verificacao numerica de 0,005 uA acima dos 100 uA nominais. Nao reestimamos Lyapunov para estes perfis; acerto ou oscilacao nao garante caos.

## Ver no LTspice

Abrir MLC_D_demo.cir com MLC_quatro_pilares.inc na mesma pasta. Passo 1: desvio de +/-1% sem correcao, 16/17 janelas. Passo 2: somente D, 17/17. Adicionar V(saida), V(referencia), V(ler) e visualizar um passo por vez. Em outro painel, adicionar V(pert_d), V(ajuste_d) e I(Bcorrecao_d) para relacionar desvio, estimativa filtrada e atuacao.

## Evidencias

Modelos, tres decks, casos JSON, logs e RAW nesta pasta. resultados.csv e resumo.json preservam medidas e classificacoes. Preparadores, analisar.py e gerar_relatorio.py reproduzem as etapas. A etapa 12 compara os coordenadores com A/B/C/D e sensores continuos; nao integra ainda os nove subpilares adaptativos em cada canal.
'''
(ROOT/'ETAPA11_RESULTADOS.md').write_text(text,encoding='utf-8')
print('Relatorio D salvo; janelas:',len(rows))
