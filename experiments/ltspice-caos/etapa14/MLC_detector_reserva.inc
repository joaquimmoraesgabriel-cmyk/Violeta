* MLC, quatro canais comportamentais; D corrige deriva da curva g(x).
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.param latencia=50u tau=100u erro_a=0.0002 erro_b=-0.0002 erro_c=0.0002 erro_d=0.00002 orcamento_max=100u
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
Blocal ganho_local 0 V={min(1,cap_operacao/max(V(pedido_total),1p))}
BesperadoY esperado_y 0 V={V(demanda_y)*V(ganho_local)}
BesperadoD esperado_d 0 V={V(demanda_d)*V(ganho_local)}
* Somente este bloco injeta falha. O detector nao recebe falha_coord nem janela.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bmult multiplicador 0 V={if(janela(time),if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(esperado_y),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreD pre_d 0 V={absdelay(V(esperado_d),if(falha_coord==2,500u,0))*V(multiplicador)}
Bheartbeat heartbeat 0 V={if(falha_coord==1,1-janela(time),1)}
Bpretotal sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
* A reserva usa seus calculos atuais; nao os comandos defeituosos do topo.
BselY selecionado_y 0 V={if(V(reserva_ativa)>0.5,V(esperado_y),V(pre_y))}
BselD selecionado_d 0 V={if(V(reserva_ativa)>0.5,V(esperado_d),V(pre_d))}
BokY ok_y 0 V={if(V(selecionado_y)*V(demanda_y)<-1e-18,0,V(selecionado_y))}
BokD ok_d 0 V={if(V(selecionado_d)*V(demanda_d)<-1e-18,0,V(selecionado_d))}
Bguard ganho_guard 0 V={min(1,cap_operacao/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
BguardF guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(selecionado_y)*V(demanda_y)<-1e-18,1,if(V(selecionado_d)*V(demanda_d)<-1e-18,1,0)))}
BcmdY comando_y 0 V={V(ok_y)*V(ganho_guard)}
BcmdD comando_d 0 V={V(ok_d)*V(ganho_guard)}
* Atuacao ideal da ablacao; shunts reais, sondas de 0 V para verificacao externa.
Bcorrecao_y 0 n_y I={V(comando_y)}
Bcorrecao_d 0 n_d I={V(comando_d)}
RmedY n_y br_y {r_med}
RmedD n_d br_d {r_med}
Vsensey br_y y 0
Vsensed br_d x 0
BmedY med_y 0 V={V(n_y,br_y)/r_med}
BmedD med_d 0 V={V(n_d,br_d)/r_med}
* Grandezas do detector escaladas: 100 uA corresponde a 1 V.
BobsY obs_y 0 V={escala_med*(V(med_y)+erro_med+ruido_med*sin(2*pi*13007*time))}
BobsD obs_d 0 V={escala_med*(V(med_d)-erro_med+ruido_med*sin(2*pi*17011*time+0.7))}
BexpY exp_y 0 V={escala_med*V(esperado_y)}
BexpD exp_d 0 V={escala_med*V(esperado_d)}
RobsY obs_y obs_y_f 1000
CobsY obs_y_f 0 {tau_med/1000} IC=0
RobsD obs_d obs_d_f 1000
CobsD obs_d_f 0 {tau_med/1000} IC=0
RexpY exp_y exp_y_f 1000
CexpY exp_y_f 0 {tau_med/1000} IC=0
RexpD exp_d exp_d_f 1000
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
Borcamento orcamento 0 V={abs(V(med_y))+abs(V(med_d))}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-11 abstol=1e-12

.options threads=1
