from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
T=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
R=list(csv.DictReader((ROOT/'janelas.csv').open(encoding='utf-8-sig')))
for r in R:
    for k in ['falha_coord','janela']:r[k]=int(r[k])
    for k in ['passo','x_inicial','margem']:r[k]=float(r[k])
    assert r['acerto'] in ['True','False','1','0'],r['acerto']
    r['acerto']=r['acerto'] in ['True','1']
assert sum(r['acerto'] for r in R)==sum(t['corretas'] for t in T)
S={s['arquivo']:s for s in json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))}

def family(names):
    ts=[t for t in T if t['arquivo'] in names]
    rows=[r for r in R if r['arquivo'] in names]
    key=lambda r:(r['falha_coord'],r['x_inicial'],r['janela'])
    paired={s:{key(r):r['acerto'] for r in rows if r['passo']==s} for s in [1.25e-6,.625e-6]}
    a,b=paired.values();assert a.keys()==b.keys()
    result=dict(trajetorias=len(ts),corretas=sum(t['corretas'] for t in ts),janelas=len(rows),
        comuns=sum(a[k] and b[k] for k in a),discordantes=sum(a[k]!=b[k] for k in a),pares=len(a),
        por_falha={str(f):sum(t['corretas'] for t in ts if t['falha_coord']==f) for f in [0,4,2,3]},
        por_passo={str(s):sum(v.values()) for s,v in paired.items()})
    for m in ['rms_residuo_d_uA','rms_residuo_y_uA','variacao_g_por_s','rms_g']:
        result[m]=float(np.mean([t[m] for t in ts]))
    return result

families={label:family([prefix+str(f) for f in [0,4,2,3]]) for label,prefix in
          [('referencia','BUF_p3_f'),('comum_E','C_comum_f'),('grupos_E','G_emprestimo_f')]}
base={(r['falha_coord'],r['passo'],r['x_inicial'],r['janela']):r['acerto'] for r in R if r['arquivo'].startswith('BUF_p3_f')}
for label,prefix in [('comum_E','C_comum_f'),('grupos_E','G_emprestimo_f')]:
    rows=[r for r in R if r['arquivo'] in [prefix+str(f) for f in [0,4,2,3]]]
    families[label]['recuperadas']=sum(r['acerto'] and not base[(r['falha_coord'],r['passo'],r['x_inicial'],r['janela'])] for r in rows)
    families[label]['novas_falhas']=sum(not r['acerto'] and base[(r['falha_coord'],r['passo'],r['x_inicial'],r['janela'])] for r in rows)

def refinement(names):
    rows=[r for r in R if r['arquivo'] in names]
    steps=sorted({r['passo'] for r in rows},reverse=True)
    maps=[{(r['x_inicial'],r['janela']):r['acerto'] for r in rows if r['passo']==s} for s in steps]
    assert all(m.keys()==maps[0].keys() for m in maps)
    return dict(passos_us=[s*1e6 for s in steps],corretas=[sum(m.values()) for m in maps],
        comuns_tres=sum(all(m[k] for m in maps) for k in maps[0]),
        discordancias=[sum(a[k]!=b[k] for k in a) for a,b in zip(maps[:-1],maps[1:])])

refined={label:refinement(names) for label,names in [
    ('referencia',['BUF_p3_f0','R_base']),('comum_E',['C_comum_f0','R_C_comum']),
    ('grupos_E',['G_emprestimo_f0','R_G_emprestimo'])]}
new=[t for t in T if t['origem']=='etapa17']
labels={'referencia':'Referencia anterior (dois atuadores)', 'comum_E':'Comum + supervisor associado a E', 'grupos_E':'Dois grupos + supervisor associado a E'}
lines=['ETAPA 17 — COORDENADOR ASSOCIADO A E, ORCAMENTO DE 90 uA','',
       f'Execucao: {len(new)} trajetorias completas novas; {len(T)-len(new)} trajetorias anteriores reanalisadas. '
       f'{len(R)} janelas no conjunto documentado. Ensaio de inicializacao SMOKE (2 casos de 1 ms) separado, sem nota logica.',
       'Todos os resultados abaixo sao de LTspice 26.1.1 e dos arquivos locais preservados.','',
       f"Resultado principal: comum associado a E {families['comum_E']['corretas']}/272, "
       f"referencia anterior {families['referencia']['corretas']}/272 e grupos com emprestimo {families['grupos_E']['corretas']}/272. "
       'O saldo de apenas uma janela no comum nao estabelece ganho robusto: houve 39 recuperacoes e 38 novas falhas. '
       'O terceiro passo manteve a sensibilidade logica. A variacao total de g(x) ficou praticamente igual no comum.',
       'Decisao: manter a coordenacao comum como base e estudar E como reserva/supervisao com validacao independente '
       'das cotas. Queda de heartbeat e gasto duplicado foram detectados; cotas enviesadas e atrasadas passaram sem alarme. '
       'A regra L2 instantanea chegou a 53/68 no piloto saudavel, mas caiu a 49/68 com o filtro e ainda exige ampliacao dos testes.','',
       '1. PERGUNTA E IMPLEMENTACAO','',
       'Um coordenador de recursos associado a E distribui cotas; os coordenadores locais calculam/aplicam as correcoes. '
       'Ele recebe o pedido assinado combinado de A/B/C e o pedido de D. E usa suas nove replicas para sua reserva local.',
       'Comum proporcional: qY=90*|Y|/(|Y|+|D|), qD=90-qY. Dois grupos fixos: 45/45. '
       'Dois grupos com emprestimo: qY=45+max(0,45-|D|)-max(0,45-|Y|), qD=90-qY, em uA. '
       'Quando ambos excedem 45, mantem-se 45/45 antes da reserva E.',
       'Na comparacao principal e no piloto de grupos, usa-se transporte de 20 us e filtro RC de 50 us na fracao de Y; D recebe o complemento. '
       'O teto exploratorio de E e 5 uA, dentro dos 90. E entra se D excede a cota e concorda no sinal; '
       'o arbitro final debita E de Y quando necessario. Isso preserva uma prioridade limitada a D e pode prejudicar A/B/C.',
       'Portanto, 45/45 descreve as cotas iniciais Y/D: com E fornecendo 5 uA, a divisao efetiva pode chegar a '
       '40 uA em ABC e 50 uA em D+E. Essa mesma regra vale durante o fallback do supervisor.',
       'O grupo fisico e ABC / D+E, porque A/B/C atuam no mesmo estado Y e podem cancelar pedidos assinados. '
       'Nao foi testado AB / CD neste lote. A mudanca de agrupamento impede atribuir esses resultados a todos os desenhos de dois grupos.',
       'A comparacao implementa politicas e interfaces funcionais, sem modelar dois processadores independentes. '
       'Na matriz principal, a falha comum do topo afeta os comandos Y e D nos dois desenhos; '
       'os testes adicionais anulam o comando de apenas um grupo por vez, mantendo o calculo local de reserva. '
       'Nao se extrai probabilidade de falha de hardware deste lote deterministico.',
       'Apenas mudar o nome/local do coordenador nao produz ganho. O novo comum tambem introduz atraso/filtro; '
       'o controle E_cota5_f0 da etapa16 identifica a condicao anterior sem essa camada.','',
       '2. COMPARACAO PRINCIPAL — ALTA DEMANDA, QUATRO CONDICOES DO TOPO','',
       'Cada linha: 16 trajetorias x 17 janelas = 272. Saudavel, queda silenciosa, atraso permanente de 500 us e inversao. '
       'Duas condicoes iniciais e dois passos maximos (1.25/0.625 us).',
       'Arquitetura | Total /272 | saudavel /68 | queda /68 | atraso /68 | inversao /68 | comuns /136 | discordantes /136']
for k,v in families.items():
    lines.append(f"{labels[k]} | {v['corretas']} | "+' | '.join(str(v['por_falha'][str(f)]) for f in [0,4,2,3])+f" | {v['comuns']} | {v['discordantes']}")
lines += ['', 'Compensacao: media dos RMS de cada trajetoria; menor residual e melhor, mas nao garante a logica.',
          'Arquitetura | residual D+E uA | residual Y uA | RMS g(x) | variacao total g(x)/s']
for k,v in families.items():
    lines.append(f"{labels[k]} | {v['rms_residuo_d_uA']:.4f} | {v['rms_residuo_y_uA']:.4f} | {v['rms_g']:.6f} | {v['variacao_g_por_s']:.3f}")
for k in ['comum_E','grupos_E']:
    v=families[k];lines.append(f"{labels[k]}: recuperou {v['recuperadas']} janelas da referencia e introduziu {v['novas_falhas']} novas falhas nas mesmas condicoes.")
lines += ['', '3. CONTROLES SAUDAVEIS E NUMERICO','',
          'Caso | corretas /68 | comuns /34 | discordantes /34 | residual D+E uA | residual Y uA']
for name in ['BUF_p3_f0','E_cota5_f0','C_comum_f0','G_fixo_f0','G_emprestimo_f0','G_sem_atuacao_E','L2_filtrado','L2_instantaneo']:
    v=S[name];p=v['pares'][0]
    lines.append(f"{name} | {v['corretas']} | {p['acertos_ambos']} | {p['divergencias']} | {v['rms_residuo_d_uA']:.3f} | {v['rms_residuo_y_uA']:.3f}")
lines += ['', 'G_sem_atuacao_E usa cap_e=0 (comando de E nulo), mantendo o terceiro atuador e os sensores no modelo. '
          'Essa ablacao nao equivale a remover fisicamente o ramo E.',
          'Ajuste exploratorio apos o piloto: regra L2, registrada em MOTIVO_AJUSTE.txt antes da execucao. '
          'Sob escassez, qY=clip((90+|Y|-|D|)/2,0,90), qD=90-qY. Esta projecao minimiza o erro quadratico '
          'dos pedidos estimados antes do filtro e da reserva E. E ainda pode retirar ate 5 uA de Y depois disso; '
          'portanto, a concessao final nao e declarada otima para a planta verdadeira. '
          'O modo filtrado mantem 20/50 us; o instantaneo ignora esse transporte/filtro e e um limite ideal. '
          'Os atuadores continuam com seus modelos anteriores. A projecao foi conferida em 10000 pares contra '
          'uma malha independente de 1001 concessoes. Esses oito ensaios sao somente saudaveis, sem terceiro passo '
          'ou matriz completa de falhas: nao se comparam seus totais de 68 com o total principal de 272.']
lines += ['','Terceiro passo: cada contagem tem denominador 34; nao e um lote de 272.']
for k,v in refined.items():
    lines.append(f"{labels[k]}: passos {v['passos_us']} us; corretas {v['corretas']}; comuns nos tres {v['comuns_tres']}/34; discordancias entre vizinhos {v['discordancias']}.")
lines += ['Diferencas entre trajetorias caoticas nao sao prova isolada de erro do solver. Entretanto, '
          'janelas que mudam de classificacao com o passo nao sustentam validacao logica independente da discretizacao.',
          '', '4. FALHAS DO SUPERVISOR E DOS GRUPOS','',
          'Ensaios exploratorios de duas condicoes iniciais no passo 0.625 us, 34 janelas por caso. '
          'Queda/duplo gasto/cota enviesada: 343.35 a 403.35 ms. Atraso extra de cotas: 500 us desde o inicio. '
          'O validador consulta somente heartbeat, faixa e soma das mensagens. Cotas invalidas retornam a 45/45 sem memoria. '
          'O validador e combinacional ideal: a latencia observada proxima do instante da injecao nao e especificacao de comparador real. '
          'Queda e inversao do topo usam detector por discrepancia com memoria, preservado da etapa15.',
          f"Controle saudavel de grupos no mesmo passo 0.625 us: {S['G_emprestimo_f0']['por_passo'][str(.625e-6)]}/34.",
          'Caso | corretas /34 | recuperadas / novas falhas versus controle | validador acionou (trajetorias) | pico pedido de cotas uA | pico concessao final uA | alarmes do detector de atuacao']
resource_results={}
resource_control={(r['x_inicial'],r['janela']):r['acerto'] for r in R if r['arquivo']=='G_emprestimo_f0' and r['passo']==.625e-6}
for name in json.loads((ROOT/'lotes_falhas_recursos.json').read_text(encoding='utf-8')):
    part=[t for t in new if t['arquivo']==name]
    rr=[r for r in R if r['arquivo']==name]
    recovered=sum(r['acerto'] and not resource_control[(r['x_inicial'],r['janela'])] for r in rr)
    regressed=sum(not r['acerto'] and resource_control[(r['x_inicial'],r['janela'])] for r in rr)
    resource_results[name]=dict(corretas=sum(t['corretas'] for t in part),recuperadas=recovered,novas_falhas=regressed,
        validador=sum(t['validador_durante'] for t in part),detector_atuacao=sum(t['reserva_retida'] for t in part))
    lines.append(f"{name} | {sum(t['corretas'] for t in part)} | {recovered} / {regressed} | {sum(t['validador_durante'] for t in part)}/2 | "
                 f"{max(t['pico_mensagens_uA'] for t in part):.5f} | {max(t['pico_concessao_uA'] for t in part):.5f} | "
                 f"{sum(t['reserva_retida'] for t in part)}/2")
lines += ['O teste enviesado envia 0 uA para Y e 90 uA para D mantendo heartbeat. '
          'Essa mensagem e contabilmente valida. O detector de atuacao compara com a referencia ja alocada; '
          'portanto, nao e um verificador independente da qualidade da cota. Melhor nota casual sob uma falha '
          'nao demonstra tolerancia nem justifica essa politica.',
          'Associar o supervisor a E tambem cria uma dependencia comum aos grupos. O ensaio de queda do supervisor '
          'nao desliga fisicamente E, sua alimentacao e seus sensores. Nao representa falha completa do pilar.',
          '', '5. CORRENTES, DETECCAO E EVIDENCIA','',
          f"Novas trajetorias: {len(new)}. Falhas de corrente por shunt/resistor/sonda: "
          f"{sum(t['corrente_falha'] for t in new)}/{sum(t['corrente_falha_resistores'] for t in new)}/{sum(t['corrente_falha_sondas'] for t in new)}. "
          f"Picos respectivos: {max(t['pico_tensoes_uA'] for t in new):.6f} / {max(t['pico_resistores_uA'] for t in new):.6f} / {max(t['pico_sondas_uA'] for t in new):.6f} uA.",
          f"Pico de soma dos comandos concedidos: {max(t['pico_concessao_uA'] for t in new):.6f} uA. "
          f"Pico de comando E: {max(t['pico_comando_e_uA'] for t in new):.6f} uA.",
          'A soma dos comandos e reconstruida de campos float32 do RAW; o desvio de aproximadamente 0.000005 uA '
          'no valor armazenado e compativel com essa resolucao. As regras algebricas limitam a concessao a 90 uA. '
          'O pico fisico informado acima e uma medida distinta e fica ligeiramente acima do nominal.',
          f"Alarmes de atuacao antes de falhas do topo ou sem falha de atuacao: {sum(t['alarme_indevido'] for t in new)}. "
          f"Validador de cotas antes da janela de falha: {sum(t['validador_antes'] for t in new)}.",
          'O limite operacional e 90 uA; o criterio numerico herdado e <=100.005 uA para soma dos MODULOS das correntes reais. '
          'Picos ligeiramente maiores que 90 devem ser informados, mesmo quando aprovados no criterio de seguranca. '
          'Nao se confunde corrente liquida em X com soma das correntes D e E.',
          f"Maior divergencia pontual shunt-resistor: {max(t['diferenca_resistores_uA'] for t in new):.6f} uA; "
          f"shunt-sonda zero volt: {max(t['diferenca_sondas_uA'] for t in new):.6f} uA. "
          'A etapa16 identificou discrepancias pontuais de sonda em passos extremamente curtos. '
          'Os residuais sao calculados por tensao no shunt / 1 kohm; os outros metodos sao auditorias independentes de pico.',
          'O analisador exige fim de cada trajetoria em 0.85 s, todas as medidas de janela e valores finitos, e rejeita '
          'avisos de tolerancia relaxada, matriz singular ou passo pequeno demais. O verificador estatico ensaiou '
          '600000 alocacoes adversas e conferiu limites e ausencia de acesso do controlador aos codigos de falha ou resposta AND esperada.',
          '', '6. LIMITES PARA A FUTURA PLACA','',
          'Ainda ha operadores ideais (abs/min/max/divisao/mediana), cotas complementares atomicas, fontes ideais e amplificadores genericos. '
          'O supervisor esta associado a E apenas na arquitetura funcional. Nao ha chip, trilha, consumo quiescente, aquecimento ou EMC validados.',
          'Os 90 uA sao de atuacao, nao do consumo total da placa. Implementacao futura deve verificar mensagens de geracoes diferentes, '
          'cotas expiradas, prioridade local, shunts/offsets/compliance, alimentacao e falhas comuns. '
          'Nove sensores E sao explicitos; A-D ainda sao replicas individuais favoraveis. Os 45 subpilares continuam uma proposta, nao uma validacao completa.',
          'A variacao total de g(x) e um indicador dinamico do modelo; nao mede dissipacao, temperatura ou vida util de componentes.',
          '', '7. REPRODUCAO','',
          'preparar_etapa17.py -> preparar_expansao.py -> preparar_ajuste.py -> verificar_regras.py -> verificar_ajuste.py. Executar cada lotes_*.json com executar.ps1 '
          '(-Slot/-Slots para filas). Depois analisar_etapa17.py, gerar_relatorio.py e verificar_entrega.py. '
          'A execucao do LTspice precisou sair do isolamento; o ensaio curto SMOKE confirmou a inicializacao. '
          'Os primeiros processos isolados foram interrompidos sem gerar resultados do lote.',
          'Artefatos: MLC_coordenador_E.inc, netlists .cir, parametros .json, logs .log, ondas .raw, '
          'trajetorias.json, janelas.csv, resumo.json, comparacoes.json, verificacao_regras.json, verificacao_entrega.json. '
          'Fontes herdadas: etapa16/MLC_pilar_E_v2.inc, etapa15/BUF_p3_f*.raw e etapa16/E_cota5_f0.raw/R_base.raw.', '',
          '8. DECISAO DE PESQUISA','',
          'Manter a coordenacao comum como base de comparacao para A/B/C/D. Os grupos ABC / D+E testados '
          'nao justificam substituir essa base. A referencia anterior permanece preservada; o supervisor associado a E '
          'e uma variante de pesquisa, com requisitos novos de validacao das cotas.',
          'A ideia de E e util para estudar reserva local e fiscalizacao de recursos. Deve existir uma unica autoridade '
          'sobre cada concessao de corrente; acrescentar um supervisor que tambem altere comandos sem essa regra '
          'cria disputa e dependencias. Neste modelo as referencias do detector foram tomadas depois da cota aceita, '
          'evitando que a reducao autorizada de corrente seja tratada como falha do topo. Isso tambem explica a cegueira '
          'a uma cota errada, mas formalmente valida.',
          'Prioridade seguinte: verificar idade e coerencia das cotas com referencia independente, definir fallback '
          'local e modelar tempos/offsets reais do validador. A regra L2 merece uma varredura de latencia e novos '
          'cenarios; seu ganho no limite instantaneo nao autoriza substituir a referencia nem declarar convergencia.',
          'Conclusao limitada a este lote deterministico: nao escolhe chip, nao prova superioridade universal de uma '
          'hierarquia e nao encerra a validacao logica ou fisica do sistema.', '']
(ROOT/'comparacoes.json').write_text(json.dumps(dict(familias=families,refinamento=refined,falhas_recursos=resource_results),indent=2),encoding='utf-8')
(ROOT/'ETAPA17_RESULTADOS.txt').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(familias=families,refinamento=refined),indent=2))
