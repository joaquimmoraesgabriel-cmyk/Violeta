* Revisao: E respeita tambem a cota ja comprometida com D.
* MLC, quatro canais comportamentais; D corrige deriva da curva g(x).
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.param latencia={lat_s} tau={tau_s} erro_a={0.0002*esc_erro} erro_b={-0.0002*esc_erro} erro_c={0.0002*esc_erro} erro_d={0.00002*esc_erro} orcamento_max=100u
.func g(z) {externo*z+(interno-externo)/2*(abs(z+1)-abs(z-1))}
Cx x 0 1u IC={x_inicial}
Cy y 0 1u IC={y_inicial}
Bx 0 x I={1u/escala*(V(y)-(1+V(pert_d))*g(V(x)))}
By 0 y I={1u/escala*(-amortecimento*(1+V(pert_a))*V(y)-V(x)+bias+V(pert_b)+entrada_amp*(2*V(entrada_a)-1+2*V(entrada_b)-1)+(forca+V(pert_c))*sin(omega*time/escala))}
Va_dist pert_a 0 SINE(0 {amp_a} 500)
Vb_dist pert_b 0 SINE(0 {amp_b} 137 0 0 40)
Vc_dist pert_c 0 SINE(0 {amp_c} 73 0 0 65)
Vd_dist pert_d 0 SINE(0 {amp_d} 211 0 0 17)
Vprobe topo 0 1
Breplica topo sensor_a I={(V(topo)-V(sensor_a))/(1000*(1+V(pert_a))*(1+erro_a))}
Rpadrao sensor_a 0 1000
BestA estimativa_a 0 V={1/V(sensor_a)-2}
BsensorB estimativa_b 0 V={V(pert_b)+erro_b}
BsensorC estimativa_c 0 V={V(pert_c)+erro_c}
BsensorD estimativa_d 0 V={V(pert_d)+erro_d}
BdelayA atrasado_a 0 V={absdelay(V(estimativa_a),latencia)}
BdelayB atrasado_b 0 V={absdelay(V(estimativa_b),latencia)}
BdelayC atrasado_c 0 V={absdelay(V(estimativa_c),latencia)}
BdelayD atrasado_d 0 V={absdelay(V(estimativa_d),latencia)}
RlagA atrasado_a ajuste_a 1000
ClagA ajuste_a 0 {tau/1000} IC=0
RlagB atrasado_b ajuste_b 1000
ClagB ajuste_b 0 {tau/1000} IC=0
RlagC atrasado_c ajuste_c 1000
ClagC ajuste_c 0 {tau/1000} IC=0
RlagD atrasado_d ajuste_d 1000
ClagD ajuste_d 0 {tau/1000} IC=0
BdemandaA demanda_a 0 V={1u/escala*amortecimento*V(ajuste_a)*V(y)*mod(topologia,2)}
BdemandaB demanda_b 0 V={1u/escala*V(ajuste_b)*mod(floor(topologia/2),2)}
BdemandaC demanda_c 0 V={1u/escala*V(ajuste_c)*sin(omega*time/escala)*mod(floor(topologia/4),2)}
BdemandaD demanda_d 0 V={1u/escala*V(ajuste_d)*g(V(x))*mod(floor(topologia/8),2)}
* Dois pedidos assinados. O calculo local de reserva continua ativo.
.param r_med=1000 escala_med=10000 tau_med=4u tau_confirmacao=10u erro_med=0.5u ruido_med=0.5u
BdemandaY demanda_y 0 V={V(demanda_a)-V(demanda_b)-V(demanda_c)}
Bpedido pedido_total 0 V={abs(V(demanda_y))+abs(V(demanda_d))}
* Nove sensores E e mediana exata por ordenacao; nao e o seletor adaptativo da etapa 9.
BEs0 e_sensor0 0 V={V(pert_d)+erro_d+(-8e-06)+erro_comum_e+(if(falhas_e>=1,0.02,0))}
BEs1 e_sensor1 0 V={V(pert_d)+erro_d+(-6e-06)+erro_comum_e+(if(falhas_e>=2,0.02,0))}
BEs2 e_sensor2 0 V={V(pert_d)+erro_d+(-4e-06)+erro_comum_e+(if(falhas_e>=3,0.02,0))}
BEs3 e_sensor3 0 V={V(pert_d)+erro_d+(-2e-06)+erro_comum_e+(if(falhas_e>=4,0.02,0))}
BEs4 e_sensor4 0 V={V(pert_d)+erro_d+(0.0)+erro_comum_e+(if(falhas_e>=5,0.02,0))}
BEs5 e_sensor5 0 V={V(pert_d)+erro_d+(2e-06)+erro_comum_e+(0)}
BEs6 e_sensor6 0 V={V(pert_d)+erro_d+(4e-06)+erro_comum_e+(0)}
BEs7 e_sensor7 0 V={V(pert_d)+erro_d+(6e-06)+erro_comum_e+(0)}
BEs8 e_sensor8 0 V={V(pert_d)+erro_d+(8e-06)+erro_comum_e+(0)}
BElo0_0 e_sort0_0 0 V={min(V(e_sensor0),V(e_sensor1))}
BEhi0_0 e_sort0_1 0 V={max(V(e_sensor0),V(e_sensor1))}
BElo0_2 e_sort0_2 0 V={min(V(e_sensor2),V(e_sensor3))}
BEhi0_2 e_sort0_3 0 V={max(V(e_sensor2),V(e_sensor3))}
BElo0_4 e_sort0_4 0 V={min(V(e_sensor4),V(e_sensor5))}
BEhi0_4 e_sort0_5 0 V={max(V(e_sensor4),V(e_sensor5))}
BElo0_6 e_sort0_6 0 V={min(V(e_sensor6),V(e_sensor7))}
BEhi0_6 e_sort0_7 0 V={max(V(e_sensor6),V(e_sensor7))}
BElo1_1 e_sort1_1 0 V={min(V(e_sort0_1),V(e_sort0_2))}
BEhi1_1 e_sort1_2 0 V={max(V(e_sort0_1),V(e_sort0_2))}
BElo1_3 e_sort1_3 0 V={min(V(e_sort0_3),V(e_sort0_4))}
BEhi1_3 e_sort1_4 0 V={max(V(e_sort0_3),V(e_sort0_4))}
BElo1_5 e_sort1_5 0 V={min(V(e_sort0_5),V(e_sort0_6))}
BEhi1_5 e_sort1_6 0 V={max(V(e_sort0_5),V(e_sort0_6))}
BElo1_7 e_sort1_7 0 V={min(V(e_sort0_7),V(e_sensor8))}
BEhi1_7 e_sort1_8 0 V={max(V(e_sort0_7),V(e_sensor8))}
BElo2_0 e_sort2_0 0 V={min(V(e_sort0_0),V(e_sort1_1))}
BEhi2_0 e_sort2_1 0 V={max(V(e_sort0_0),V(e_sort1_1))}
BElo2_2 e_sort2_2 0 V={min(V(e_sort1_2),V(e_sort1_3))}
BEhi2_2 e_sort2_3 0 V={max(V(e_sort1_2),V(e_sort1_3))}
BElo2_4 e_sort2_4 0 V={min(V(e_sort1_4),V(e_sort1_5))}
BEhi2_4 e_sort2_5 0 V={max(V(e_sort1_4),V(e_sort1_5))}
BElo2_6 e_sort2_6 0 V={min(V(e_sort1_6),V(e_sort1_7))}
BEhi2_6 e_sort2_7 0 V={max(V(e_sort1_6),V(e_sort1_7))}
BElo3_1 e_sort3_1 0 V={min(V(e_sort2_1),V(e_sort2_2))}
BEhi3_1 e_sort3_2 0 V={max(V(e_sort2_1),V(e_sort2_2))}
BElo3_3 e_sort3_3 0 V={min(V(e_sort2_3),V(e_sort2_4))}
BEhi3_3 e_sort3_4 0 V={max(V(e_sort2_3),V(e_sort2_4))}
BElo3_5 e_sort3_5 0 V={min(V(e_sort2_5),V(e_sort2_6))}
BEhi3_5 e_sort3_6 0 V={max(V(e_sort2_5),V(e_sort2_6))}
BElo3_7 e_sort3_7 0 V={min(V(e_sort2_7),V(e_sort1_8))}
BEhi3_7 e_sort3_8 0 V={max(V(e_sort2_7),V(e_sort1_8))}
BElo4_0 e_sort4_0 0 V={min(V(e_sort2_0),V(e_sort3_1))}
BEhi4_0 e_sort4_1 0 V={max(V(e_sort2_0),V(e_sort3_1))}
BElo4_2 e_sort4_2 0 V={min(V(e_sort3_2),V(e_sort3_3))}
BEhi4_2 e_sort4_3 0 V={max(V(e_sort3_2),V(e_sort3_3))}
BElo4_4 e_sort4_4 0 V={min(V(e_sort3_4),V(e_sort3_5))}
BEhi4_4 e_sort4_5 0 V={max(V(e_sort3_4),V(e_sort3_5))}
BElo4_6 e_sort4_6 0 V={min(V(e_sort3_6),V(e_sort3_7))}
BEhi4_6 e_sort4_7 0 V={max(V(e_sort3_6),V(e_sort3_7))}
BElo5_1 e_sort5_1 0 V={min(V(e_sort4_1),V(e_sort4_2))}
BEhi5_1 e_sort5_2 0 V={max(V(e_sort4_1),V(e_sort4_2))}
BElo5_3 e_sort5_3 0 V={min(V(e_sort4_3),V(e_sort4_4))}
BEhi5_3 e_sort5_4 0 V={max(V(e_sort4_3),V(e_sort4_4))}
BElo5_5 e_sort5_5 0 V={min(V(e_sort4_5),V(e_sort4_6))}
BEhi5_5 e_sort5_6 0 V={max(V(e_sort4_5),V(e_sort4_6))}
BElo5_7 e_sort5_7 0 V={min(V(e_sort4_7),V(e_sort3_8))}
BEhi5_7 e_sort5_8 0 V={max(V(e_sort4_7),V(e_sort3_8))}
BElo6_0 e_sort6_0 0 V={min(V(e_sort4_0),V(e_sort5_1))}
BEhi6_0 e_sort6_1 0 V={max(V(e_sort4_0),V(e_sort5_1))}
BElo6_2 e_sort6_2 0 V={min(V(e_sort5_2),V(e_sort5_3))}
BEhi6_2 e_sort6_3 0 V={max(V(e_sort5_2),V(e_sort5_3))}
BElo6_4 e_sort6_4 0 V={min(V(e_sort5_4),V(e_sort5_5))}
BEhi6_4 e_sort6_5 0 V={max(V(e_sort5_4),V(e_sort5_5))}
BElo6_6 e_sort6_6 0 V={min(V(e_sort5_6),V(e_sort5_7))}
BEhi6_6 e_sort6_7 0 V={max(V(e_sort5_6),V(e_sort5_7))}
BElo7_1 e_sort7_1 0 V={min(V(e_sort6_1),V(e_sort6_2))}
BEhi7_1 e_sort7_2 0 V={max(V(e_sort6_1),V(e_sort6_2))}
BElo7_3 e_sort7_3 0 V={min(V(e_sort6_3),V(e_sort6_4))}
BEhi7_3 e_sort7_4 0 V={max(V(e_sort6_3),V(e_sort6_4))}
BElo7_5 e_sort7_5 0 V={min(V(e_sort6_5),V(e_sort6_6))}
BEhi7_5 e_sort7_6 0 V={max(V(e_sort6_5),V(e_sort6_6))}
BElo7_7 e_sort7_7 0 V={min(V(e_sort6_7),V(e_sort5_8))}
BEhi7_7 e_sort7_8 0 V={max(V(e_sort6_7),V(e_sort5_8))}
BElo8_0 e_sort8_0 0 V={min(V(e_sort6_0),V(e_sort7_1))}
BEhi8_0 e_sort8_1 0 V={max(V(e_sort6_0),V(e_sort7_1))}
BElo8_2 e_sort8_2 0 V={min(V(e_sort7_2),V(e_sort7_3))}
BEhi8_2 e_sort8_3 0 V={max(V(e_sort7_2),V(e_sort7_3))}
BElo8_4 e_sort8_4 0 V={min(V(e_sort7_4),V(e_sort7_5))}
BEhi8_4 e_sort8_5 0 V={max(V(e_sort7_4),V(e_sort7_5))}
BElo8_6 e_sort8_6 0 V={min(V(e_sort7_6),V(e_sort7_7))}
BEhi8_6 e_sort8_7 0 V={max(V(e_sort7_6),V(e_sort7_7))}
BEmed estimativa_e 0 V={V(e_sort8_4)}
BEdelay atrasado_e 0 V={absdelay(V(estimativa_e),latencia)}
RElag atrasado_e ajuste_e 1000
CElag ajuste_e 0 {tau/1000} IC=0
BdemandaE demanda_e 0 V={1u/escala*V(ajuste_e)*g(V(x))}
* Coordenador de recursos associado a E: cotas normalizadas, soma unica.
* arquitetura=0 proporcional comum; 1 grupos fixos; 2 grupos com emprestimo.
* A/B/C sao combinados ANTES da alocacao, preservando cancelamentos assinados.
BfracCom frac_com 0 V={abs(V(demanda_y))/max(V(pedido_total),1p)}
BfracGrp frac_grp 0 V={limit(0.5+(max(0,cap_operacao/2-abs(V(demanda_d)))-max(0,cap_operacao/2-abs(V(demanda_y))))/cap_operacao,0,1)}
BfracL2 frac_l2 0 V={if(V(pedido_total)<=cap_operacao,V(frac_com),limit(0.5+(abs(V(demanda_y))-abs(V(demanda_d)))/(2*cap_operacao),0,1))}
BfracAlvo frac_alvo 0 V={if(politica_l2,V(frac_l2),V(frac_com))}
Btransporte frac_atrasada 0 V={absdelay(V(frac_alvo),lat_coord)}
Rquota frac_atrasada frac_filtro 1000
Cquota frac_filtro 0 {tau_coord/1000} IC=0.5
* Falhas do supervisor: 1 queda com heartbeat; 2 atraso extra; 3 duplo gasto; 4 cota valida enviesada.
Bfracao frac_recebida 0 V={absdelay(V(frac_filtro),if(falha_super==2,500u,if(falha_super==5,500u,0)))}
BmodoQ modo_quota 0 V={if(janela(time),falha_super,0)}
BqY q_msg_y 0 V={if(V(modo_quota)==1,0,if(V(modo_quota)==3,cap_operacao,if(V(modo_quota)==4,0,if(V(modo_quota)==6,limit(cap_operacao*V(frac_recebida)+12u,0,cap_operacao),cap_operacao*V(frac_recebida)))))}
BqD q_msg_d 0 V={if(V(modo_quota)==1,0,if(V(modo_quota)==3,cap_operacao,if(V(modo_quota)==4,cap_operacao,if(V(modo_quota)==6,cap_operacao-limit(cap_operacao*V(frac_recebida)+12u,0,cap_operacao),cap_operacao*(1-V(frac_recebida))))))}
BhbQ hb_quota 0 V={if(falha_super==1,1-janela(time),1)}
* Metadados injetados apenas aqui: falha 2 atrasa valor e marca; 5 so valor.
BstampTx stamp_tx 0 V={time}
BstampRx stamp_rx 0 V={absdelay(V(stamp_tx),lat_coord+if(falha_super==2,500u,0))}
* Validador nao recebe codigo/horario da falha: heartbeat, faixa e soma das mensagens.
BqInval quota_invalida 0 V={if(V(hb_quota)<0.5,1,if(min(V(q_msg_y),V(q_msg_d))<-1n,1,if(V(q_msg_y)+V(q_msg_d)>cap_operacao+1n,1,0)))}
* MONITOR INDEPENDENTE: usa mensagens, demandas medidas e relogio local.
* Independencia funcional, nao de sensores, alimentacao ou tecnologia.
BqRefCom q_ref_com 0 V={abs(V(demanda_y))/max(abs(V(demanda_y))+abs(V(demanda_d)),1p)}
BqRefL2 q_ref_l2 0 V={if(abs(V(demanda_y))+abs(V(demanda_d))<=cap_operacao,V(q_ref_com),limit(0.5+(abs(V(demanda_y))-abs(V(demanda_d)))/(2*cap_operacao),0,1))}
BqRef q_ref_alvo 0 V={if(politica_l2,V(q_ref_l2),V(q_ref_com))}
BqRefDelay q_ref_atrasada 0 V={absdelay(V(q_ref_alvo),lat_coord+lat_ref_extra)}
RqRef q_ref_atrasada q_ref_filtro 1000
CqRef q_ref_filtro 0 {tau_coord*(1+tol_ref)/1000} IC=0.5
* Buffers: o observador nao carrega o RC da referencia.
BqExpY q_exp_y 0 V={escala_med*cap_operacao*V(q_ref_filtro)}
BqExpD q_exp_d 0 V={escala_med*cap_operacao*(1-V(q_ref_filtro))}
BqObsY q_obs_y 0 V={escala_med*(V(q_msg_y)+offset_q+ruido_q*sin(2*pi*13007*time))}
BqObsD q_obs_d 0 V={escala_med*(V(q_msg_d)-offset_q+ruido_q*sin(2*pi*17011*time+0.7))}
RqEY q_exp_y q_exp_y_f 1000
CqEY q_exp_y_f 0 4n IC=0
RqED q_exp_d q_exp_d_f 1000
CqED q_exp_d_f 0 4n IC=0
RqOY q_obs_y q_obs_y_f 1000
CqOY q_obs_y_f 0 4n IC=0
RqOD q_obs_d q_obs_d_f 1000
CqOD q_obs_d_f 0 4n IC=0
BqErro erro_cota 0 V={(abs(V(q_obs_y_f)-V(q_exp_y_f))+abs(V(q_obs_d_f)-V(q_exp_d_f)))/escala_med}
BqLimiar limiar_cota 0 V={2u+0.05*cap_operacao}
BqCoer incoerente 0 V={if(V(erro_cota)>V(limiar_cota),1,0)}
BclockRx clock_rx 0 V={time*(1+drift_ppm*1e-6)+clock_offset}
BqAge idade_cota 0 V={V(clock_rx)-V(stamp_rx)}
BqVelha idade_invalida 0 V={if(V(idade_cota)>80u,1,if(V(idade_cota)<-30u,1,0))}
BqRazao razao_cota 0 V={if(time>2m,max(V(quota_invalida),max(V(incoerente),V(idade_invalida))),0)}
CqTimer timer_cota 0 1n IC=0
BqTimer 0 timer_cota I={if(V(razao_cota)>0.5,(1-V(timer_cota))/(50u/1n),-V(timer_cota)/(20u/1n))}
BqTrip trip_cota 0 V={if(V(timer_cota)>0.7,1,0)}
CqMem memoria_cota 0 1n IC=0
BqMem 0 memoria_cota I={max(V(trip_cota)-V(memoria_cota),0)/1000}
RqMem memoria_cota 0 1T
BqReserva reserva_cota 0 V={if(diagnostico_cotas,if(V(memoria_cota)>0.5,1,0),0)}
* FIM MONITOR. Reserva proporcional local; guard antigo permanece durante confirmacao.
BquotaY quota_y 0 V={if(V(reserva_cota)>0.5,cap_operacao*V(q_ref_com),if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_y),0,cap_operacao)))}
BquotaD quota_d 0 V={if(V(reserva_cota)>0.5,cap_operacao*(1-V(q_ref_com)),if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_d),0,cap_operacao)))}
BbaseY base_y 0 V={sgn(V(demanda_y))*min(abs(V(demanda_y)),V(quota_y))}
BbaseD base_d 0 V={sgn(V(demanda_d))*min(abs(V(demanda_d)),V(quota_d))}
* E mantem reserva local de ate 5 uA. A arbitragem final debita E de Y quando necessario.
* Nao ha um segundo pedido ao topo nem uma segunda concessao da mesma corrente.
Bdeficit deficit_d 0 V={max(0,abs(V(demanda_e))-abs(V(base_d))-1u)}
BesperadoE esperado_e 0 V={if(abs(V(demanda_d))>abs(V(base_d))+1u,if(V(demanda_e)*V(demanda_d)>0,sgn(V(demanda_e))*min(cap_e,min(V(deficit_d),max(0,cap_operacao-abs(V(base_d))))),0),0)}
BesperadoY esperado_y 0 V={sgn(V(base_y))*min(abs(V(base_y)),max(0,cap_operacao-abs(V(base_d))-abs(V(esperado_e))))}
BesperadoD esperado_d 0 V={V(base_d)}
Bsaldo saldo_concedido 0 V={cap_operacao-abs(V(esperado_y))-abs(V(esperado_d))-abs(V(esperado_e))}
* Somente este bloco injeta falha. O detector nao recebe falha_coord nem janela.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bmult multiplicador 0 V={if(janela(time),if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(esperado_y),if(alvo_topo==2,0,if(falha_coord==2,500u,0)))*if(alvo_topo==2,1,V(multiplicador))}
BpreD pre_d 0 V={absdelay(V(esperado_d),if(alvo_topo==1,0,if(falha_coord==2,500u,0)))*if(alvo_topo==1,1,V(multiplicador))}
Bheartbeat heartbeat 0 V={if(falha_coord==1,1-janela(time),1)}
Bpretotal sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
* A reserva usa seus calculos atuais; nao os comandos defeituosos do topo.
BselY selecionado_y 0 V={if(V(reserva_ativa)>0.5,V(esperado_y),V(pre_y))}
BselD selecionado_d 0 V={if(V(reserva_ativa)>0.5,V(esperado_d),V(pre_d))}
BokY ok_y 0 V={if(V(selecionado_y)*V(demanda_y)<-1e-18,0,V(selecionado_y))}
BokD ok_d 0 V={if(V(selecionado_d)*V(demanda_d)<-1e-18,0,V(selecionado_d))}
Bguard ganho_guard 0 V={min(1,max(0,cap_operacao-abs(V(esperado_e)))/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
BguardF guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(selecionado_y)*V(demanda_y)<-1e-18,1,if(V(selecionado_d)*V(demanda_d)<-1e-18,1,0)))}
BcmdY comando_y 0 V={V(ok_y)*V(ganho_guard)}
BcmdD comando_d 0 V={V(ok_d)*V(ganho_guard)}
BcmdE comando_e 0 V={V(esperado_e)}
* Circuito de atuacao: modelo ADI, shunt, isolador, RC e realimentacao.
.include atuadores_etapa14.inc
.param margem_limite=90u gbw_limit=100Meg tau_cmd=2u
Vp vp 0 5
Vm vm 0 -5
Rstart vp partida 100k
Cstart partida 0 100p IC=0
Bready habilitado 0 V={if(V(partida)>3,if(V(vp)>4,1,0),0)}
BnormY norm_y 0 V={escala_med*V(comando_y)}
BnormD norm_d 0 V={escala_med*V(comando_d)}
RcmdY norm_y filtro_y 1000
CcmdY filtro_y 0 {tau_cmd/1000} IC=0
RcmdD norm_d filtro_d 1000
CcmdD filtro_d 0 {tau_cmd/1000} IC=0
BphyY phy_y 0 V={V(filtro_y)/escala_med*V(ganho_fisico)}
BphyD phy_d 0 V={V(filtro_d)/escala_med*V(ganho_fisico)}
XY phy_y br_y vp vm med_y habilitado ATUADOR
XD phy_d br_d vp vm med_d habilitado ATUADOR
BnormE norm_e 0 V={escala_med*V(comando_e)}
RcmdE norm_e filtro_e 1000
CcmdE filtro_e 0 {tau_cmd/1000} IC=0
BphyE phy_e 0 V={V(filtro_e)/escala_med*V(ganho_fisico)}
XE phy_e br_e vp vm med_e habilitado ATUADOR
Vsensee br_e x 0
.include limitador_tres.inc
XL med_y med_d med_e vp vm ganho_fisico LIMITADOR3
Vsensey br_y y 0
Vsensed br_d x 0
* Grandezas do detector escaladas: 100 uA corresponde a 1 V.
BobsY obs_y 0 V={escala_med*(V(med_y)+erro_med+ruido_med*sin(2*pi*13007*time))}
BobsD obs_d 0 V={escala_med*(V(med_d)-erro_med+ruido_med*sin(2*pi*17011*time+0.7))}
BexpY exp_y_cmd 0 V={escala_med*V(esperado_y)}
RexpCmdY exp_y_cmd exp_y 1000
CexpCmdY exp_y 0 {tau_cmd/1000} IC=0
BexpD exp_d_cmd 0 V={escala_med*V(esperado_d)}
RexpCmdD exp_d_cmd exp_d 1000
CexpCmdD exp_d 0 {tau_cmd/1000} IC=0
RobsY obs_y obs_y_f 1000
CobsY obs_y_f 0 {tau_med/1000} IC=0
RobsD obs_d obs_d_f 1000
CobsD obs_d_f 0 {tau_med/1000} IC=0
BisolY exp_y_buf 0 V={V(exp_y)}
RexpY exp_y_buf exp_y_f 1000
CexpY exp_y_f 0 {tau_med/1000} IC=0
BisolD exp_d_buf 0 V={V(exp_d)}
RexpD exp_d_buf exp_d_f 1000
CexpD exp_d_f 0 {tau_med/1000} IC=0
Berro discrepancia 0 V={abs(V(obs_y_f)-V(exp_y_f))+abs(V(obs_d_f)-V(exp_d_f))}
Blimiar limiar 0 V={escala_med*3u+0.1*(abs(V(exp_y_f))+abs(V(exp_d_f)))}
Bdiv divergente 0 V={if(time>2m,if(abs(V(exp_y_f))+abs(V(exp_d_f))>escala_med*5u,if(V(discrepancia)>V(limiar),1,0),0),0)}
* Confirmacao RC, seguida de memoria. Reset requer intervencao futura.
Ctimer timer 0 1n IC=0
Btimer 0 timer I={if(V(divergente)>0.5,(1-V(timer))/(tau_confirmacao/1n),-V(timer)/(2*tau_confirmacao/1n))}
Btrip trip 0 V={if(V(timer)>0.7,1,0)}
Cmem memoria 0 1n IC=0
Bmem 0 memoria I={max(V(trip)-V(memoria),0)/1000}
Rmem memoria 0 1T
Breserva reserva_ativa 0 V={if(detector,if(V(memoria)>0.5,1,0),0)}
Borcamento orcamento 0 V={abs(V(med_y))+abs(V(med_d))+abs(V(med_e))}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-11 abstol=1e-12

.options threads=1
