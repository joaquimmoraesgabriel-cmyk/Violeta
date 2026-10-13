"""Relatorio cruzado gerado dos resultados auditados, sem descartar pilotos reprovados."""
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent

def main():
    ts=json.loads((ROOT/'trajetorias.json').read_text(encoding='utf-8'))
    ss=json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))
    sums={s['arquivo']:s for s in ss}
    with (ROOT/'janelas.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    out=[]
    def line(s=''):out.append(s)
    def table(headers,items):
        data=[list(map(str,headers))]+[list(map(str,r)) for r in items]
        widths=[max(len(r[i]) for r in data) for i in range(len(headers))]
        for i,r in enumerate(data):
            line(' | '.join(x.ljust(w) for x,w in zip(r,widths)))
            if i==0:line('-+-'.join('-'*w for w in widths))
        line()
    def family(prefix):
        names=[prefix+str(f) for f in [0,4,2,3]]
        group=[sums[n] for n in names]
        return dict(nomes=names,acertos=sum(g['corretas'] for g in group),janelas=sum(g['janelas'] for g in group),
                    divergencias=sum(g['pares'][0]['divergencias'] for g in group),
                    comuns=sum(g['pares'][0]['acertos_ambos'] for g in group),
                    rms_d=sum(g['rms_residuo_d_uA'] for g in group)/4,
                    rms_y=sum(g['rms_residuo_y_uA'] for g in group)/4,
                    rms_g=sum(g['rms_g'] for g in group)/4,
                    variacao_g=sum(g['variacao_g_por_s'] for g in group)/4,
                    falsos=sum(g['alarmes_indevidos'] for g in group))
    families={label:family(prefix) for label,prefix in [('Referência etapa 15','BUF_p3_f'),('Pilar E revisado','E_v2_f'),('Prioridade D, 2 atuadores','D_v2_f')]}
    matched={}
    def logical_map(names):
        return {(r['falha_coord'],r['passo'],r['x_inicial'],r['janela']):int(r['acerto']) for r in rows if r['arquivo'] in names}
    base_map=logical_map(families['Referência etapa 15']['nomes'])
    for label,data in families.items():
        if label=='Referência etapa 15':continue
        candidate_map=logical_map(data['nomes']);assert base_map.keys()==candidate_map.keys()
        matched[label]=dict(recuperadas=sum(not base_map[k] and candidate_map[k] for k in base_map),
                            novas_falhas=sum(base_map[k] and not candidate_map[k] for k in base_map))
    line('ETAPA 16 — PILAR E, MEDIÇÃO E CAPACIDADE')
    line('Relatório de pesquisa no LTspice. Correntes em µA; passos máximos em µs.')
    line()
    new=[t for t in ts if t['origem']=='etapa16']
    line(f'{len(new)} trajetórias novas ({len(new)*17} janelas), mais 16 trajetórias históricas reanalisadas (272 janelas).')
    line('Uma trajetória dura 850 ms. A sequência, as duas condições iniciais e a regra de leitura foram mantidas.')
    line('Cada janela exige o sinal correto de x durante todo o intervalo de leitura, não apenas na média.')
    line()
    baseline=families['Referência etapa 15'];candidate=families['Pilar E revisado']
    line('DECISÃO DE PESQUISA')
    line(f"E revisado reduziu o resíduo RMS de D em {100*(1-candidate['rms_d']/baseline['rms_d']):.1f}%, mas elevou o resíduo de A–B–C em {100*(candidate['rms_y']/baseline['rms_y']-1):.1f}%.")
    line(f"A lógica ficou em {candidate['acertos']}/272 contra {baseline['acertos']}/272. A variação total de g(x) mudou {100*(candidate['variacao_g']/baseline['variacao_g']-1):+.3f}% na média.")
    line('O benefício local em D não basta para aprovar a arquitetura na demanda original. A revisão da cota e o ajuste para 5 µA foram testados, preservando os resultados anteriores.')
    line('Manter E como candidato de reserva especializada, sem adicioná-lo à arquitetura principal nesta etapa. Priorizar a repartição x/y e a margem lógica dentro da capacidade disponível, usando novos casos e refinamento numérico para validar qualquer mudança.')
    line('Os ensaios com menor perturbação ajudam a delimitar a faixa de funcionamento; não substituem o requisito de suportar a alta demanda original. A mediana ajuda contra erros individuais, mas não elimina o erro comum.')
    line()
    line('1. COMPARAÇÃO PRINCIPAL: ALTA DEMANDA, QUATRO CONDIÇÕES DO TOPO')
    table(['Arquitetura','Acertos','Comuns nos 2 passos','Divergências /136','Resíduo D RMS','Resíduo Y RMS','g RMS (V)','Variação g (V/s)','Falsos'],
          [[k,f"{v['acertos']}/{v['janelas']}",f"{v['comuns']}/136",v['divergencias'],f"{v['rms_d']:.3f}",f"{v['rms_y']:.3f}",f"{v['rms_g']:.4f}",f"{v['variacao_g']:.2f}",v['falsos']] for k,v in families.items()])
    table(['Condição','Referência /68','E revisado /68','Prioridade D /68'],
          [[label,sums[f'BUF_p3_f{f}']['corretas'],sums[f'E_v2_f{f}']['corretas'],sums[f'D_v2_f{f}']['corretas']] for f,label in [(0,'Saudável'),(4,'Silêncio com heartbeat'),(2,'Atraso permanente de 500 µs'),(3,'Inversão')]])
    line('A referência de 198/272 veio dos RAWs corrigidos da etapa 15; não foi substituída por uma repetição favorável.')
    line('O total de 272 inclui quatro condições x dois passos x dois estados iniciais x 17 janelas.')
    line('Acertos comuns contam apenas pares que acertam nos dois passos. Divergências contam mudança de classificação.')
    line('Pequenas diferenças de contagem entre arquiteturas equivalentes em atuação não demonstram superioridade universal em um sistema sensível ao passo.')
    table(['Contra a mesma janela da referência','Recuperadas','Novas falhas'],[[k,v['recuperadas'],v['novas_falhas']] for k,v in matched.items()])
    line()
    line('2. COMO E FOI REPRESENTADO')
    line('E é um terceiro atuador sobre x, dedicado a corrigir a falta de D. Recebe a estimativa local e a cota de D; seu comando não passa pelo topo.')
    line('Só atua quando |pedido D| supera |cota D| em mais de 1 µA, no mesmo sentido. Não recebe a verdade lógica nem o código ou horário da falha.')
    line('Saturação aqui significa falta de cota para atender o pedido de D; não é um detector físico de saída encostada no rail ou de falha interna do amplificador.')
    line('E fixo reserva 20 µA e deixa 70 µA para Y/D. E revisado conserva a cota proporcional de D, usa até 20 µA do espaço restante e retira essa parcela de Y.')
    line('Se D não precisa de E, o orçamento fica disponível aos canais principais. A versão revisada também limita E por 90 µA menos a cota já comprometida com D.')
    line('O controle de prioridade soma o mesmo pedido ao atuador D, mantendo dois atuadores; o pedido adicional segue o caminho de comando e failover já existente em D. E usa seu ramal local dedicado, inclusive antes da entrada do failover. Assim comparamos alocação e autonomia.')
    line('A contagem de corrente inclui |IY|+|ID|+|IE|; E não recebe corrente adicional gratuita. Não estamos medindo consumo da alimentação ou energia armazenada.')
    line('A conexão exclusiva a D vale para o pedido de correção. E compartilha alimentação e limitador global; sua cota é contabilizada na proteção de recursos.')
    line()
    line('3. PILOTOS E REVISÃO PRESERVADOS')
    table(['Piloto saudável','Acertos /68','Divergências /34','Resíduo D','Resíduo Y','Falsos'],
          [[n,sums[n]['corretas'],sums[n]['pares'][0]['divergencias'],f"{sums[n]['rms_residuo_d_uA']:.3f}",f"{sums[n]['rms_residuo_y_uA']:.3f}",sums[n]['alarmes_indevidos']] for n in ['E_fixo_f0','E_livre_f0','D_prioridade_f0']])
    line('A verificação estática encontrou até 109,9964 µA na soma das referências da primeira reserva livre, antes da guarda de comando. Não é uma medida de corrente física.')
    line('A guarda continuava limitando a atuação, mas podia divergir da referência do detector. A revisão corrige essa inconsistência e passou em 100.000 entradas por modo.')
    line('As versões piloto não foram sobrescritas. REVISAO_ALOCACAO.txt e verificacao_regras.json preservam o diagnóstico.')
    line('Após observar redução do resíduo de D e aumento do resíduo de Y no controle de prioridade, foi testada uma cota menor para E: 5 µA.')
    table(['Ajuste exploratório, topo saudável','Acertos /68','Divergências /34','Resíduo D','Resíduo Y'],
          [[n,sums[n]['corretas'],sums[n]['pares'][0]['divergencias'],f"{sums[n]['rms_residuo_d_uA']:.3f}",f"{sums[n]['rms_residuo_y_uA']:.3f}"] for n in ['BUF_p3_f0','E_v2_f0','E_cota5_f0']])
    line('A cota de 5 µA foi escolhida como um único ajuste após o piloto, sem varredura para maximizar acertos. Não foi expandida às quatro condições do topo nem ao terceiro passo; não misturar seus resultados com os de 20 µA.')
    line()
    line('4. ERRO FIXO, ATRASO E INTENSIDADE DAS PERTURBAÇÕES')
    table(['Condição saudável','Acertos /68','Divergências /34','Resíduo D','Resíduo Y'],
          [[n,sums[n]['corretas'],sums[n]['pares'][0]['divergencias'],f"{sums[n]['rms_residuo_d_uA']:.3f}",f"{sums[n]['rms_residuo_y_uA']:.3f}"] for n in ['BUF_p3_f0','S_sem_offset','S_rapido','S_rapido_sem_offset','C_demanda75','C_demanda50','E_demanda75']])
    line('Rápido: latência de 50 para 5 µs e RC de 100 para 10 µs, mantendo a capacidade de 90 µA. Sem offset: erros fixos de A–D zerados.')
    line('Demanda 75/50: todas as amplitudes das quatro perturbações reduzidas juntas. Não confundir redução da perturbação com aumento de corrente disponível.')
    line('Estas são ablações favoráveis para diagnóstico. Ainda não incluem o custo/ruído de sensores físicos mais rápidos.')
    table(['Condição saudável','Demanda exata >91 µA, % do tempo','Excesso médio sobre 90 µA'],
          [[n,f"{100*sum(t['fracao_demanda_real_acima_90'] for t in ts if t['arquivo']==n)/4:.2f}",
            f"{sum(t['media_excesso_demanda_real_uA'] for t in ts if t['arquivo']==n)/4:.3f}"] for n in ['BUF_p3_f0','E_v2_f0','S_rapido','C_demanda75','C_demanda50']])
    line('A demanda exata é calculada após a simulação com as perturbações injetadas e o estado de cada trajetória. Não alimenta nenhum controlador nem constitui um novo ensaio de capacidade física.')
    line()
    line('5. TERCEIRO PASSO: 0,3125 µs, TOPO SAUDÁVEL')
    refinement=[]
    for label,normal,fine in [('Referência','BUF_p3_f0','R_base'),('E revisado','E_v2_f0','R_E_v2'),('Sensores rápidos','S_rapido','R_rapido')]:
        chosen=[r for r in rows if r['arquivo'] in [normal,fine]]
        maps={s:{(r['x_inicial'],r['janela']):int(r['acerto']) for r in chosen if float(r['passo'])==s} for s in [1.25e-6,.625e-6,.3125e-6]}
        a,b,c=maps.values();assert a.keys()==b.keys()==c.keys()
        refinement.append(dict(nome=label,acertos=[sum(m.values()) for m in maps.values()],divergencias=[sum(a[k]!=b[k] for k in a),sum(b[k]!=c[k] for k in a)],comuns_tres=sum(a[k] and b[k] and c[k] for k in a)))
    table(['Candidato','1,25 /34','0,625 /34','0,3125 /34','Mudanças 1→2','Mudanças 2→3','Comuns aos 3 /34'],
          [[r['nome'],*r['acertos'],*r['divergencias'],r['comuns_tres']] for r in refinement])
    line('Refinar o passo máximo não prova convergência ponto a ponto de uma trajetória caótica. As divergências lógicas restantes são falhas abertas de robustez.')
    line()
    line('6. NOVE SENSORES E E A PROPOSTA DE 45 SUBPILARES')
    line('E tem nove fontes comportamentais de leitura e mediana exata em LTspice. Erros individuais fixos vão de -0,000008 a +0,000008, além do erro comum de D.')
    line('O grupo mantém erro comum e compartilha o parâmetro verdadeiro favorável; não são nove chips físicos ou fontes independentes de informação.')
    line('Quatro falhas: as primeiras quatro leituras recebem +0,02. Erro comum: todas recebem +0,002. Condições mantidas durante todo o transiente.')
    table(['Condição E, passo 0,625','Acertos /34','Sensor E: erro RMS','Resíduo D','Resíduo Y'],
          [[n,sum(t['corretas'] for t in ts if t['arquivo']==n and t['passo']==.625e-6),
            f"{sum(t['rms_erro_sensor_e'] for t in ts if t['arquivo']==n and t['passo']==.625e-6)/2:.8f}",
            f"{sum(t['rms_residuo_d_uA'] for t in ts if t['arquivo']==n and t['passo']==.625e-6)/2:.3f}",
            f"{sum(t['rms_residuo_y_uA'] for t in ts if t['arquivo']==n and t['passo']==.625e-6)/2:.3f}"] for n in ['E_v2_f0','E_quatro_falhas','E_erro_comum']])
    line('A/B/C/D continuam com uma réplica cada. 45 = 5 x 9 é a arquitetura candidata; o conjunto completo e o seletor adaptativo ainda não foram integrados.')
    line('A mediana foi verificada em todos os 512 vetores binários e em 9.488 vetores adicionais. Isso comprova a regra de ordenação, não a independência física dos sensores.')
    line()
    line('7. CORRENTE, DETECTOR E MÉTRICAS DINÂMICAS')
    line(f"Pico pelas tensões dos shunts, nas {len(new)} trajetórias novas: {max(t['pico_tensoes_uA'] for t in new):.6f} µA.")
    for key,label in [('corrente_falha','tensões dos shunts'),('corrente_falha_resistores','correntes dos resistores'),('corrente_falha_sondas','sondas de 0 V')]:
        line(f"Violações de 100,005 µA por {label}: {sum(t[key] for t in new)}/{len(new)}.")
    line(f"Maior diferença instantânea shunts/resistores: {max(t['diferenca_resistores_uA'] for t in new):.6f} µA; shunts/sondas: {max(t['diferenca_sondas_uA'] for t in new):.6f} µA.")
    line('As três leituras passam no teto, mas suas formas de onda não coincidem perfeitamente. Os resíduos e a conclusão física de corrente usam tensão/R, conferida com a corrente dos resistores. A divergência das sondas de 0 V permanece uma limitação de medição numérica; não foi atribuída a uma sobrecorrente física confirmada. auditoria_sondas.json localiza os dois maiores casos e suas amostras vizinhas.')
    if (ROOT/'auditoria_sondas.json').exists():
        audit=json.loads((ROOT/'auditoria_sondas.json').read_text(encoding='utf-8'))
        table(['Auditoria de sonda','Instante (s)','Passo anterior (s)','Diferença RMS (µA)'],
              [[f"{a['arquivo']} caso {a['caso']}",f"{a['tempo_s']:.12g}",f"{a['dt_anterior_s']:.3e}",f"{a['rms_diferenca_uA']:.8f}"] for a in audit])
        line('Os maiores desvios aparecem em passos internos extremamente curtos; o maior ocorre na inicialização. A diferença RMS ao longo da trajetória é inferior a 0,0001 µA nos dois casos auditados. A causa interna do cálculo das sondas não foi demonstrada por este ensaio.')
    faultcases=[t for t in new if t['falha_coord']]
    line(f"Casos novos com falha do topo e reserva retida ao fim: {sum(t['reserva_retida'] for t in faultcases)}/{len(faultcases)}. Alarme não significa recuperação lógica.")
    latency_rows=[]
    for prefix,label in [('E_v2_f','E revisado'),('D_v2_f','Prioridade D')]:
        for f,fname in [(4,'Silêncio'),(2,'Atraso'),(3,'Inversão')]:
            values=[t['latencia_alarme_us'] for t in new if t['arquivo']==prefix+str(f)]
            detected=[v for v in values if v is not None]
            latency_rows.append([label,fname,f'{len(detected)}/{len(values)}',f'{min(detected):.3f}–{max(detected):.3f}' if detected else 'Nenhuma'])
    table(['Arquitetura','Falha','Detectadas','Latência de alarme (µs)'],latency_rows)
    line('Falhas temporárias começam em 343,35 ms e terminam em 403,35 ms. O atraso de 500 µs é permanente desde o início; sua latência inclui a inibição inicial de 2 ms.')
    line('Resíduo D = I_D + I_E - 0,01*pert_D*g(x); resíduo Y usa a correção exata das perturbações A–B–C. Correntes são obtidas por tensão/R dos shunts.')
    line('RMS e frações são integrados no tempo entre 30 e 850 ms. A tabela principal apresenta a média dos RMS de cada trajetória, com igual peso.')
    line('Variação de g/s = soma dos módulos dos incrementos de g(x), dividida pela duração. Também foram salvos pico de g e ocupação |x|>1 por trajetória.')
    line('As unidades de g e sua variação são equivalentes às tensões do modelo normalizado, não tensões de um chip já selecionado.')
    line('g(x) não foi redesenhada: E altera sua compensação no estado x. Estas medidas de dinâmica não representam estresse térmico, dissipação ou EMI.')
    line()
    line('8. ALCANCE PARA A FUTURA PLACA VIRTUAL')
    line('Amplificadores UniversalOpAmp2 genéricos, shunts, RCs e isoladores foram mantidos. Cálculo, mediana, sinais de medição e guardas de sinal/capacidade permanecem idealizados.')
    line('O limitador não ideal agora soma três módulos no candidato E. Compartilhar limitador e alimentação impede tratar E como redundância física completa.')
    line('O detector atual verifica Y e D; a saída E ainda não possui detecção própria de discrepância. Falhas comuns de medição não são cobertas por comparar um comando com sua atuação.')
    line('Ainda faltam chips escolhidos, falhas do próprio atuador/limitador, parasitas, térmica, ruído estatístico, tolerâncias da nova integração e a pirâmide completa de sensores.')
    line('Resultados valem para esta sequência finita e estados iniciais. Não selecionar hardware nem declarar o circuito totalmente validado apenas por essas contagens.')
    line()
    line('9. REPRODUÇÃO E FONTES')
    line('preparar_etapa16.py: pilotos. preparar_expansao.py: modelos v2 e matriz cruzada. preparar_refinamento.py: terceiro passo e sensores E. preparar_E_menor.py: ajuste exploratório de 5 µA.')
    line('executar.ps1 -Manifest lotes_piloto.json / lotes_expansao.json / lotes_refinamento.json / lotes_E_menor.json: LTspice em batch, um manifesto por chamada. Slot/Slots divide decks entre processos.')
    line('analisar_etapa16.py: logs completos, RAW completos, janelas e correntes. gerar_relatorio.py: este texto e comparacoes.json. verificar_entrega.py: integridade da entrega.')
    line('Resultados: trajetorias.json, resumo.json, janelas.csv. RAWs e logs originais preservados. Cache de análise depende do código e das datas dos arquivos de entrada.')
    line('auditar_sondas.py registra as discrepâncias entre medidores. gerar_figura.py produz comparacao_pilar_E.svg. consolidar_pesquisa.py atualiza os dois documentos existentes da pesquisa.')
    line('Documentação ADI da sintaxe .tran/.meas/.step: https://github.com/analogdevicesinc/ltspice-reference/blob/main/ai_ref/SIMULATION-COMMANDS-REFERENCE.md')
    line('As conclusões quantitativas deste relatório vêm dos arquivos locais, não da documentação externa.')
    (ROOT/'ETAPA16_RESULTADOS.txt').write_text('\n'.join(out)+'\n',encoding='utf-8')
    (ROOT/'comparacoes.json').write_text(json.dumps(dict(familias=families,pareadas=matched,refinamento=refinement),indent=2),encoding='utf-8')
    print(json.dumps(dict(familias=families,pareadas=matched,refinamento=refinement),indent=2))

if __name__=='__main__':main()
