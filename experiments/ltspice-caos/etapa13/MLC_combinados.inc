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
* A injeta em y; B e C retiram: pedido assinado y=A-B-C.
BdemandaY demanda_y 0 V={V(demanda_a)-V(demanda_b)-V(demanda_c)}
Btotal pedido_total 0 V={abs(V(demanda_y))+abs(V(demanda_d))}
Bglobal ganho_comum 0 V={min(1,orcamento_max/max(V(pedido_total),1p))}
BbaseY base_y 0 V={V(demanda_y)*V(ganho_comum)}
BbaseD base_d 0 V={V(demanda_d)*V(ganho_comum)}
* Mesmas falhas de topo da referencia, abrangendo ambos os atuadores.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bfalha falha_injetada 0 V={janela(time)}
Bmult multiplicador 0 V={if(V(falha_injetada)>0.5,if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(base_y),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreD pre_d 0 V={absdelay(V(base_d),if(falha_coord==2,500u,0))*V(multiplicador)}
Bpretotal sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
BokY ok_y 0 V={if(V(pre_y)*V(demanda_y)<-1e-18,0,V(pre_y))}
BokD ok_d 0 V={if(V(pre_d)*V(demanda_d)<-1e-18,0,V(pre_d))}
Bguard ganho_guard 0 V={min(1,orcamento_max/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
Bguardflag guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(pre_y)*V(demanda_y)<-1e-18,1,if(V(pre_d)*V(demanda_d)<-1e-18,1,0)))}
Breserva reserva_ativa 0 V=0
Bcorrecao_y 0 mede_y I={V(ok_y)*V(ganho_guard)}
Bcorrecao_d 0 mede_d I={V(ok_d)*V(ganho_guard)}
* Sondas de 0 V adicionadas pelo preparador abaixo.
Bsaida saida 0 V={if(V(x)>0,1,0)}
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-11 abstol=1e-12

.options threads=1
Vsensey mede_y y 0
Vsensed mede_d x 0
Borcamento orcamento 0 V={abs(I(Vsensey))+abs(I(Vsensed))}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}
BpedidoSeparado pedido_separado 0 V={abs(V(demanda_a))+abs(V(demanda_b))+abs(V(demanda_c))+abs(V(demanda_d))}
BpedidoLiquido pedido_liquido 0 V={abs(V(demanda_a)-V(demanda_b)-V(demanda_c))+abs(V(demanda_d))}
Bcancelamento cancelamento 0 V={max(0,V(pedido_separado)-V(pedido_liquido))}
