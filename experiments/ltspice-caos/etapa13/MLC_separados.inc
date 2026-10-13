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
* Grupos AB e CD: demandas representadas numericamente em ampere.
Bg1 pedido_grupo1 0 V={abs(V(demanda_a))+abs(V(demanda_b))}
Bg2 pedido_grupo2 0 V={abs(V(demanda_c))+abs(V(demanda_d))}
Btotal pedido_total 0 V={V(pedido_grupo1)+V(pedido_grupo2)}
Bglobal ganho_comum 0 V={min(1,orcamento_max/max(V(pedido_total),1p))}
* Politica 2: emprestimo informado por demandas de 50 us atras.
Bquota1 quota1 0 V={orcamento_max/2+max(0,orcamento_max/2-absdelay(V(pedido_grupo2),50u))}
Bquota2 quota2 0 V={orcamento_max/2+max(0,orcamento_max/2-absdelay(V(pedido_grupo1),50u))}
Blocal1 ganho1 0 V={min(1,if(politica_coord==2,V(quota1),orcamento_max/2)/max(V(pedido_grupo1),1p))}
Blocal2 ganho2 0 V={min(1,if(politica_coord==2,V(quota2),orcamento_max/2)/max(V(pedido_grupo2),1p))}
* Politica 3: ordem fixa B,D,A,C, sem acesso a resposta AND esperada.
BpriB prioridade_b 0 V={limit(V(demanda_b),-orcamento_max,orcamento_max)}
BrestB resta_b 0 V={max(0,orcamento_max-abs(V(prioridade_b)))}
BpriD prioridade_d 0 V={limit(V(demanda_d),-V(resta_b),V(resta_b))}
BrestD resta_d 0 V={max(0,V(resta_b)-abs(V(prioridade_d)))}
BpriA prioridade_a 0 V={limit(V(demanda_a),-V(resta_d),V(resta_d))}
BrestA resta_a 0 V={max(0,V(resta_d)-abs(V(prioridade_a)))}
BpriC prioridade_c 0 V={limit(V(demanda_c),-V(resta_a),V(resta_a))}
* Falhas fisicas injetadas: 1 silencio/perda de heartbeat; 2 atraso; 3 sinal invertido.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bfalha falha_injetada 0 V={janela(time)}
Bmult1 multiplicador1 0 V={if(V(falha_injetada)>0.5,if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
Bmult2 multiplicador2 0 V={if(politica_coord==1,1,if(politica_coord==2,1,V(multiplicador1)))}
* O atraso de 500 us e permanente no ensaio 2; evitar atraso variavel nao causal.
BbaseA base_a 0 V={if(politica_coord==3,V(prioridade_a),V(demanda_a)*if(politica_coord==1,V(ganho1),if(politica_coord==2,V(ganho1),V(ganho_comum))))}
BbaseB base_b 0 V={if(politica_coord==3,V(prioridade_b),V(demanda_b)*if(politica_coord==1,V(ganho1),if(politica_coord==2,V(ganho1),V(ganho_comum))))}
BbaseC base_c 0 V={if(politica_coord==3,V(prioridade_c),V(demanda_c)*if(politica_coord==1,V(ganho2),if(politica_coord==2,V(ganho2),V(ganho_comum))))}
BbaseD base_d 0 V={if(politica_coord==3,V(prioridade_d),V(demanda_d)*if(politica_coord==1,V(ganho2),if(politica_coord==2,V(ganho2),V(ganho_comum))))}
BpreA pre_a 0 V={absdelay(V(base_a),if(falha_coord==2,500u,0))*V(multiplicador1)}
BpreB pre_b 0 V={absdelay(V(base_b),if(falha_coord==2,500u,0))*V(multiplicador1)}
BpreC pre_c 0 V={absdelay(V(base_c),if(falha_coord==2,500u,0))*V(multiplicador2)}
BpreD pre_d 0 V={absdelay(V(base_d),if(falha_coord==2,500u,0))*V(multiplicador2)}
Bpretotal sem_protecao 0 V={abs(V(pre_a))+abs(V(pre_b))+abs(V(pre_c))+abs(V(pre_d))}
* Watchdog observa heartbeat e sinais de comandos; nao le a identidade da falha.
Vpulse relogio 0 PULSE(0 1 0 0.1u 0.1u 100u 200u)
Bheartbeat heartbeat 0 V={V(relogio)*if(V(falha_injetada)>0.5,if(falha_coord==1,0,1),1)}
Bcharge 0 saude I={max(V(heartbeat)-V(saude),0)/10000}
Csaude saude 0 1n IC=1
Rsaude saude 0 500k
Binval invalido 0 V={if(V(pre_a)*V(demanda_a)<-1e-18,1,if(V(pre_b)*V(demanda_b)<-1e-18,1,if(V(pre_c)*V(demanda_c)<-1e-18,1,if(V(pre_d)*V(demanda_d)<-1e-18,1,0))))}
BchargeE 0 alerta I={max(V(invalido)-V(alerta),0)/10000}
Calerta alerta 0 1n IC=0
Ralerta alerta 0 500k
Breserva reserva_ativa 0 V={if(politica_coord==4,if(V(saude)<0.3,1,if(V(alerta)>0.3,1,0)),0)}
* Reserva simples: 25 uA por canal; usa a propria demanda filtrada atual.
BcmdA comando_a 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_a),-orcamento_max/4,orcamento_max/4),V(pre_a))}
BcmdB comando_b 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_b),-orcamento_max/4,orcamento_max/4),V(pre_b))}
BcmdC comando_c 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_c),-orcamento_max/4,orcamento_max/4),V(pre_c))}
BcmdD comando_d 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_d),-orcamento_max/4,orcamento_max/4),V(pre_d))}
* Protecao comum a TODAS as politicas: rejeita sinal oposto ao pedido atual e limita soma.
BokA ok_a 0 V={if(V(comando_a)*V(demanda_a)<-1e-18,0,V(comando_a))}
BokB ok_b 0 V={if(V(comando_b)*V(demanda_b)<-1e-18,0,V(comando_b))}
BokC ok_c 0 V={if(V(comando_c)*V(demanda_c)<-1e-18,0,V(comando_c))}
BokD ok_d 0 V={if(V(comando_d)*V(demanda_d)<-1e-18,0,V(comando_d))}
Bguard ganho_guard 0 V={min(1,orcamento_max/max(abs(V(ok_a))+abs(V(ok_b))+abs(V(ok_c))+abs(V(ok_d)),1p))}
Bguardflag guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(invalido)>0.5,1,0))}
Bcorrecao_a 0 mede_a I={V(ok_a)*V(ganho_guard)}
Bcorrecao_b mede_b 0 I={V(ok_b)*V(ganho_guard)}
Bcorrecao_c mede_c 0 I={V(ok_c)*V(ganho_guard)}
Bcorrecao_d 0 mede_d I={V(ok_d)*V(ganho_guard)}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}

Bsaida saida 0 V={if(V(x)>0,1,0)}
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-11 abstol=1e-12

.options threads=1
Vsensea mede_a y 0
Vsenseb y mede_b 0
Vsensec y mede_c 0
Vsensed mede_d x 0
Borcamento orcamento 0 V={abs(I(Vsensea))+abs(I(Vsenseb))+abs(I(Vsensec))+abs(I(Vsensed))}
BpedidoSeparado pedido_separado 0 V={abs(V(demanda_a))+abs(V(demanda_b))+abs(V(demanda_c))+abs(V(demanda_d))}
BpedidoLiquido pedido_liquido 0 V={abs(V(demanda_a)-V(demanda_b)-V(demanda_c))+abs(V(demanda_d))}
Bcancelamento cancelamento 0 V={max(0,V(pedido_separado)-V(pedido_liquido))}
