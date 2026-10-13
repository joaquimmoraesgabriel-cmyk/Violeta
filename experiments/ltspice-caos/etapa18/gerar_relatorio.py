"""Relatorio cruzado gerado dos resultados completos; conclusoes revisadas a parte."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
T=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
S={s['arquivo']:s for s in json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))}
R=list(csv.DictReader((ROOT/'janelas.csv').open(encoding='utf-8-sig')))
for r in R:
    for k in ['caso','janela','falha_coord']:r[k]=int(r[k])
    for k in ['passo','x_inicial','margem']:r[k]=float(r[k])
    assert r['acerto'] in ['1','0','True','False']
    r['acerto']=r['acerto'] in ['1','True']
assert len(T)==64 and len(R)==64*17
assert sum(r['acerto'] for r in R)==sum(t['corretas'] for t in T)

def part(name):return [t for t in T if t['arquivo']==name]
def windowmap(name):return {(r['passo'],r['x_inicial'],r['janela']):r['acerto'] for r in R if r['arquivo']==name}
def crossed(base,test):
    a,b=windowmap(base),windowmap(test);assert b.keys()<=a.keys()
    return dict(base=base,test=test,janelas=len(b),controle_corretas=sum(a[k] for k in b),
        teste_corretas=sum(b.values()),recuperadas=sum(b[k] and not a[k] for k in b),
        novas_falhas=sum(a[k] and not b[k] for k in b),
        discordancias_antes_injecao=sum(a[k]!=b[k] for k in b if k[2]<6),
        janelas_antes_injecao=sum(k[2]<6 for k in b))

pairs=[('C_sadio_off','C_sadio_on'),('C_vies_off','C_vies_on'),
       ('L2_20_50_off','L2_5_10_off'),('L2_5_10_off','L2_5_10'),
       ('L2_5_10_off','L2_5_10_v2'),('L2_5_10_v2','L2_replay_v2'),('L2_5_10_v2','L2_vies_v2')]
pairs += [('C_sadio_on',name) for name in S if name.startswith('C_') and name not in ['C_sadio_on','C_sadio_off','C_vies_off']]
cross=[crossed(a,b) for a,b in pairs]

def refinement(names):
    rows=[r for r in R if r['arquivo'] in names];steps=sorted({r['passo'] for r in rows},reverse=True)
    maps=[{(r['x_inicial'],r['janela']):r['acerto'] for r in rows if r['passo']==step} for step in steps]
    assert all(m.keys()==maps[0].keys() for m in maps)
    return dict(passos_us=[s*1e6 for s in steps],corretas=[sum(m.values()) for m in maps],
        comuns_tres=sum(all(m[k] for m in maps) for k in maps[0]),
        discordancias=[sum(a[k]!=b[k] for k in a) for a,b in zip(maps[:-1],maps[1:])])
refined={label:refinement(names) for label,names in [('comum',['C_sadio_on','R_C']),('L2_monitor_ligado',['L2_5_10','R_L2_5_10'])]}

healthy=[t for t in T if t['falha_super']==0]
faulty=[t for t in T if t['falha_super'] and t['diagnostico_cotas']]
diagnostics={}
for name,s in S.items():
    rows=part(name);lat=[t['cota_latencia_alarme_us'] for t in rows if t['cota_latencia_alarme_us'] is not None]
    diagnostics[name]=dict(trajetorias=len(rows),alarmes_indevidos=sum(t['cota_alarme_indevido'] for t in rows),
        deteccoes=sum(bool(t['cota_alarme_detectado']) for t in rows),
        reservas_retidas=sum(t['cota_reserva_retida'] for t in rows),
        latencia_min_us=min(lat) if lat else None,latencia_max_us=max(lat) if lat else None,
        idade_min_us=min(t['cota_idade_min_us'] for t in rows),idade_max_us=max(t['cota_idade_max_us'] for t in rows),
        pico_erro_uA=max(t['cota_pico_erro_uA'] for t in rows),
        top_alarme_sem_falha_topo=sum(t['alarme_indevido'] for t in rows),
        idade_invalida_em_algum_momento=sum(t['cota_primeira_idade_invalida_us'] is not None for t in rows))

lines=['ETAPA 18 — FISCALIZACAO DAS COTAS E RECUPERACAO LOCAL','',
       f'LTspice 26.1.1: {len(T)} trajetorias completas novas, {len(R)} janelas logicas. '
       'SMOKE: dois casos de 1 ms apenas para inicializacao, fora de todas as notas.',
       f"Ultima amostra RAW: maior distancia ate tstop de 0.85 s = {max(t['lacuna_final_us'] for t in T):.6f} us. "
       'Cada percurso precisa de log/medidas completos e ultima amostra a no maximo um passo configurado de tstop; '
       'nenhum ponto final foi inventado. A ultima janela logica termina em 0.849 s. '
       'Ver NOTA_COBERTURA_RAW.txt.',
       'Dados: netlists, parametros JSON, logs .meas e RAWs preservados nesta pasta. '
       'Planejamento em PLANO_PREVIO.txt; oito controles adicionais justificados em ADENDO_CONTROLES_L2.txt '
       'e oito ensaios de revisao em ADENDO_CONFIRMACAO_V2.txt.','']
conclusion=ROOT/'CONCLUSAO_REVISADA.txt'
if conclusion.exists():lines += [conclusion.read_text(encoding='utf-8'),'']
lines += ['1. O QUE FOI IMPLEMENTADO','',
    'Mantida a coordenacao comum de A/B/C/D. A/B/C somam pedidos assinados para o atuador Y; D e E atuam em X. '
    'E conserva nove replicas e mediana, reserva local com comando de ate 5 uA contido no total de 90 uA. '
    'E pode retirar capacidade de Y, depois da cota inicial; nao cria corrente extra.',
    'O comum divide as cotas iniciais proporcionalmente aos modulos dos pedidos Y/D. '
    'L2 muda somente essa regra no mesmo coordenador: em sobrecarga, '
    'qY=limit((C+|pedidoY|-|pedidoD|)/2,0,C), qD=C-qY, C=90 uA; '
    'abaixo da capacidade conserva a fracao proporcional. E arbitra depois. '
    'Portanto L2 nao significa acrescentar outro coordenador ou outro orcamento.',
    'O novo fiscal recebe cotas Y/D, heartbeat e carimbo de tempo; recalcula a fracao esperada por outro caminho '
    'a partir das mesmas demandas medidas. Nao acessa codigo da falha, horario de injecao, perturbacoes verdadeiras '
    'ou a resposta logica desejada. Compartilhar demandas ainda permite falhas de causa comum.',
    'Referencia nominal: mesmo atraso/filtro do coordenador, acrescido de 2 us e 5% na constante RC. '
    'Comparacao bufferizada com RC 4 us nos dois lados. Offset +/-0.5 uA e ruido senoidal 0.5 uA por canal. '
    'Limiar da soma de discrepancias: 2 uA + 5% de 90 uA = 6.5 uA.',
    'Idade permitida: -30 a 80 us. Carimbo modelado como tempo de origem transportado; filtro da cota '
    'nao aumenta essa idade, sendo fiscalizado pelo teste de coerencia. Isso e um modelo de protocolo/clock, '
    'nao uma implementacao de sincronismo ou protecao contra falsificacao. '
    'Nos cantos +/-25 ppm e +/-10 us, a idade fica entre -11.25 e 51.25 us ate 0.85 s. '
    'Sem ressincronizacao, a propria equacao preve cruzar o limite inferior apos 1.6 s no canto negativo '
    'e o superior apos 2 s no positivo. Esses horizontes maiores nao foram simulados neste lote.',
    'A guarda antiga verifica heartbeat, faixa e soma imediatamente. Durante uma mensagem basica invalida '
    'ela usa 45/45 uA. A nova confirmacao RC sobe em 20 us, desce em 40 us, dispara a 0.7 e fica inibida '
    'nos primeiros 2 ms. Apos confirmacao, uma memoria retém a distribuicao proporcional local ate o fim. '
    'Essa e a V1. A V2 altera apenas carga/descarga para 50/20 us: disparo continuo nominal em 60.20 us '
    'a partir de zero, contra 24.08 us da V1. A memoria RC nao e persistencia digital estrita.',
    'Mesmo na familia L2, a reserva de cotas usa a regra proporcional comum. Portanto, um alarme em L2 '
    'muda efetivamente a politica. Monitor desabilitado preserva o calculo/registro do alarme, mas impede '
    'essa comutacao; nao remove os circuitos observadores nem a guarda basica.',
    'As cotas sao complementares e atomicas neste modelo. Cotas de geracoes distintas, comunicacao digital '
    'discreta, clock independente real e reset controlado ainda nao foram implementados.','',
    '2. NOTA LOGICA E SENSIBILIDADE AO PASSO','',
    'Alta demanda; cada trajetoria tem 17 blocos de 50 ms. A janela 30–49 ms exige X positivo em todo '
    'o intervalo para AND=1 e negativo em todo o intervalo para AND=0. Duas condicoes iniciais, sem '
    'reinicio entre blocos. O passo indicado e maximo permitido, com integracao adaptativa trap.',
    'Caso | trajetorias | corretas/janelas | corretas por passo maximo (s) | comuns/divergentes nos dois passos']
for name,s in S.items():
    pairs_txt='; '.join(f"{p['acertos_ambos']}/{p['divergencias']} de 34 pares" for p in s['pares']) or 'um passo'
    lines.append(f"{name} | {s['trajetorias']} | {s['corretas']}/{s['janelas']} | {s['por_passo']} | {pairs_txt}")
lines += ['','Terceiro passo: denominador 34 por passo.']
for name,r in refined.items():lines.append(f"{name}: {r}")
lines += ['O terceiro passo de L2 com monitor ligado avalia o conjunto L2 + eventual reserva, e nao L2 puro. '
          'Nao foram feitos tres passos nos controles L2 com comutacao desabilitada. '
          'A concordancia entre dois passos ou uma nota maior isolada nao estabelece convergencia.',
          '', '3. CRUZAMENTO DAS MESMAS JANELAS','',
          'Controle -> teste | notas na intersecao | recuperadas | novas falhas | divergencias em janelas 0–5']
for p in cross:
    lines.append(f"{p['base']} -> {p['test']} | {p['controle_corretas']}/{p['janelas']} -> {p['teste_corretas']}/{p['janelas']} | "
                 f"{p['recuperadas']} | {p['novas_falhas']} | {p['discordancias_antes_injecao']}/{p['janelas_antes_injecao']}")
lines += ['Janelas 0–5 terminam antes da injecao temporaria de 343.35 ms. Para atraso/replay permanentes '
          'e mudancas de politica/tolerancia essa coluna NAO representa periodo sem intervencao. '
          'Diferencas precoces mesmo entre casos nominalmente equivalentes revelam sensibilidade numerica '
          'e impedem interpretar toda diferenca posterior como efeito causal exclusivo da falha.',
          'Nos percursos saudaveis V2 em que a reserva nunca aciona, a politica efetiva e a mesma de '
          'L2_5_10_off. Os observadores sao comportamentais e nao carregam eletricamente os pedidos. '
          'Mudar seu RC ainda pode alterar os passos adaptativos do solver e a trajetoria caotica. '
          'Portanto, eventual diferenca de nota entre esses percursos nao demonstra ganho logico causal '
          'do fiscal. Sua rejeicao de alarmes e sua latencia sao avaliacoes separadas.',
          '', '4. DETECCAO, RESERVA E ALARMES INDEVIDOS','',
          'Falhas: 1 heartbeat perdido e cotas zeradas; 2 atraso extra 500 us em cota e carimbo; '
          '3 mensagens 90+90 uA; 4 cotas Y=0/D=90 com heartbeat/carimbo recentes; '
          '5 cota atrasada 500 us com carimbo recente; 6 deslocamento de ate 12 uA de D para Y.',
          'Falhas 1/3/4/6 duram 343.35–403.35 ms; 2/5 comecam em t=0. A latencia destes ultimos inclui '
          'a inibicao inicial de 2 ms. Queda simultanea tambem zera os comandos do topo com heartbeat mantido.',
          'Caso | deteccoes de falha | alarmes antes/sem falha | reserva retida | latencia min..max us | idade min..max us']
for name,d in diagnostics.items():
    lat='--' if d['latencia_min_us'] is None else f"{d['latencia_min_us']:.3f}..{d['latencia_max_us']:.3f}"
    lines.append(f"{name} | {d['deteccoes']}/{d['trajetorias']} | {d['alarmes_indevidos']}/{d['trajetorias']} | "
                 f"{d['reservas_retidas']}/{d['trajetorias']} | {lat} | {d['idade_min_us']:.3f}..{d['idade_max_us']:.3f}")
lines += ['Nos controles *_off, deteccao registrada nao significa recuperacao habilitada. '
          'Alarmes indevidos sao contados mesmo se a comutacao estiver desabilitada. '
          'Deteccao exige novo alarme dentro do intervalo de injecao, sem memoria ja armada antes; '
          'as latencias publicadas usam somente essas deteccoes. '
          'Nos dados JSON, cota_primeira_incoerencia_us e cota_primeira_idade_invalida_us '
          'sao relativas a injecao quando ha falha e a partida quando o caso e saudavel; '
          'em ambos, a busca respeita a inibicao inicial. '
          'A memoria requer reset futuro; o teste nao demonstra retorno seguro ao supervisor apos reparo.',
          f"Com fiscal habilitado: {sum(bool(t['cota_alarme_detectado']) for t in faulty)}/{len(faulty)} trajetorias com falha de cota produziram alarme.",
          f"Detector anterior de atuacao: {sum(t['alarme_indevido'] for t in T)} alarmes em trajetorias sem falha de comando do topo; "
          f"{sum(t['latencia_alarme_us'] is not None for t in T if t['falha_coord'])}/{sum(bool(t['falha_coord']) for t in T)} falhas de topo detectadas.",
          'Essas categorias distinguem um fiscal de cotas de um detector que observa a corrente depois da alocacao.',
          'Diagnostico do primeiro percurso V1: no primeiro trip saudavel, L2 5/10 us pedia 26.334 uA '
          '(Y=22.503, D=3.831) e recebia cotas 65.490/24.510 uA; L2 1/2 us pedia 19.037 uA '
          '(Y=13.237, D=5.800) e recebia cotas 59.103/30.897 uA. Ambas as cotas cobriam os pedidos '
          'naqueles instantes. O fiscal reagiu a uma diferenca na distribuicao de capacidade ociosa. '
          'Essa observacao motiva testar futuramente discrepancia na concessao efetiva min(pedido,cota), '
          'sem desabilitar as verificacoes de idade/heartbeat/soma. Essa alternativa NAO foi simulada nesta etapa. '
          'Valores reproduziveis por diagnosticar_inicio.py, no RAW, caso 0.', '',
          'Nos quatro primeiros disparos dos cantos saudaveis, incoerente=1, idade_invalida=0 '
          'e quota_invalida=0. As cotas Y/D cobriam os respectivos pedidos naquele instante. '
          'A confirmacao tem memoria de instantes anteriores; essa observacao reforca a hipotese '
          'de comparar concessoes efetivas, mas nao testa tal alternativa. '
          'Ver diagnosticar_tolerancias.py e diagnostico_tolerancias.json.', '',
          '5. CORRENTES E COMPENSACAO','',
          'Caso | pico corrente real uA | RMS residual Y uA | RMS residual D+E uA | RMS g(x) | variacao total g(x)/s']
for name,s in S.items():
    lines.append(f"{name} | {s['pico_corrente_uA']:.6f} | {s['rms_residuo_y_uA']:.4f} | {s['rms_residuo_d_uA']:.4f} | {s['rms_g']:.6f} | {s['variacao_g_por_s']:.3f}")
lines += [f"Picos gerais: tensao/shunt {max(t['pico_tensoes_uA'] for t in T):.8f} uA; "
          f"corrente do resistor {max(t['pico_resistores_uA'] for t in T):.8f} uA; "
          f"sondas 0 V {max(t['pico_sondas_uA'] for t in T):.8f} uA.",
          f"Falhas frente ao teto legado 100.005 uA: tensoes {sum(t['corrente_falha'] for t in T)}, "
          f"resistores {sum(t['corrente_falha_resistores'] for t in T)}, sondas {sum(t['corrente_falha_sondas'] for t in T)}.",
          f"Maximo das cotas aceitas {max(t['pico_cotas_aceitas_uA'] for t in T):.8f} uA; "
          f"concessao final Y+D+E {max(t['pico_concessao_uA'] for t in T):.8f} uA; "
          f"comando E {max(t['pico_comando_e_uA'] for t in T):.8f} uA.",
          f"Pico fisico de E, por tensao/shunt: {max(t['pico_e_uA'] for t in T):.8f} uA. "
          'O limite de 5 uA do comando nao equivale a um teto fisico instantaneo comprovado.',
          f"Maior diferenca ponto a ponto: tensao/shunt versus resistor {max(t['diferenca_resistores_uA'] for t in T):.6f} uA; "
          f"versus sonda 0 V {max(t['diferenca_sondas_uA'] for t in T):.6f} uA.",
          '90 uA e a cota operacional dos atuadores. Pequenos excessos fisicos acima de 90 nao sao escondidos '
          'pelo criterio legado de 100.005. Os numeros de corrente somam modulos dos tres ramos, sem cancelamento '
          'de D e E, e nao representam o consumo total dos sensores, amplificadores ou processadores.',
          'O maior pico nas sondas 0 V ocorre em C_tolerancia_mais, caso 1, em 84.439588369402 ms: '
          '90.804677 uA, contra 90.000515 uA nos resistores naquele ponto. O passo anterior e '
          '6.38e-16 s. Ha divergencias tambem nas amostras vizinhas, com shunts quase constantes. '
          'Isso sugere uma dificuldade numerica, mas nenhuma amostra foi descartada e a causa '
          'nao foi isolada por uma nova simulacao. A metrologia exige investigacao antes de '
          'atribuir precisao fisica aos picos. Ver auditar_pico_sondas.py e diagnostico_pico_sondas.json.',
          'RMS residuais usam perturbacoes verdadeiras apenas na analise posterior, nunca no fiscal. '
          'Valores agregados sao medias dos RMS por trajetoria. A variacao total de g(x) e uma medida '
          'dinamica matematica, nao dissipacao, estresse termico ou envelhecimento do hardware.','',
          '6. CONTEXTO ANTERIOR E LIMITES','',
          'Etapa17: matriz de quatro condicoes do topo: referencia 198/272, comum+E 199/272 e grupos+E 174/272. '
          'Os novos testes mudam o fiscal e a matriz de falhas; nenhum total de 68 ou 34 e comparado diretamente '
          'a 198/272. L2 anterior 49/68 com 20/50 us e 53/68 ideal serve apenas de contexto. '
          'A comparacao de latencia desta etapa usa L2_20_50_off e L2_5_10_off no MESMO modelo novo.',
          'Os atuadores mantem amplificadores genericos, shunts, RC e realimentacao; o nucleo MLC, sinais, calculos, '
          'comparadores e varias protecoes ainda sao comportamentais. Os 45 subpilares continuam conceito: '
          'somente E possui nove replicas explicitas, A–D usam um sensor favoravel cada.',
          'Este lote nao valida chips escolhidos, barramentos reais, falha fisica de atuador, alimentacoes '
          'independentes, parasitas de trilha, dissipacao termica, EMC ou uma placa PCB. A proxima realizacao '
          'fisica deve considerar a faixa dinamica e os atrasos encontrados aqui, sem confundir nota logica '
          'ou fiscal comportamental com validacao completa de hardware.','',
          'Reproducao: executar.ps1 recebe um manifesto por chamada; os quatro lotes e a copia segura '
          'dos arquivos estao descritos em REPRODUCAO.txt. analisar_etapa18.py rejeita resultados incompletos '
          'ou avisos numericos; verificar_entrega.py audita a entrega. verificar_modelo.py verificou '
          '600000 alocacoes e a separacao estrutural entre injecao e fiscal.',
          'Correcao metodologica: indicadores booleanos agora sao convertidos a float antes da integracao '
          'temporal. Foram recalculadas 162 trajetorias unicas dos arquivos antigos e corrigidos 184 registros '
          'das etapas16/17, com backups. A tabela de demanda >91 uA da referencia saudavel passou de 31.12% '
          'para 62.15% do tempo. Contagens, alarmes, picos, RMS e variacao de g(x) nao foram alterados. '
          'Ver ERRATA_INTEGRACAO_INDICADORES.txt e correcao_fracoes_anteriores.json.']
(ROOT/'comparacoes.json').write_text(json.dumps(dict(cruzamentos=cross,refinamento=refined,diagnosticos=diagnostics),indent=2),encoding='utf-8')
(ROOT/'ETAPA18_RESULTADOS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Relatorio e comparacoes gerados.')
