* Porta MLC, dois canais e uma camada de alocacao de corrente.
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.param latencia=50u tau=100u erro_a=0.0002 erro_b=-0.0002
.param amp_a=table(perfil,0,0.005,1,0.0015,2,0.010,3,0.015)
.param amp_b=table(perfil,0,0.006,1,0.010,2,0.001,3,0.012)
.func g(z) {externo*z+(interno-externo)/2*(abs(z+1)-abs(z-1))}
Cx x 0 1u IC={x_inicial}
Cy y 0 1u IC={y_inicial}
Bx 0 x I={1u/escala*(V(y)-g(V(x)))}
By 0 y I={1u/escala*(-amortecimento*(1+V(pert_a))*V(y)-V(x)+bias+V(pert_b)+entrada_amp*(2*V(entrada_a)-1+2*V(entrada_b)-1)+forca*sin(omega*time/escala))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
Va_dist pert_a 0 SINE(0 {amp_a} 500)
Vb_dist pert_b 0 SINE(0 {amp_b} 137 0 0 40)
Vprobe topo 0 1
Breplica topo sensor_a I={(V(topo)-V(sensor_a))/(1000*(1+V(pert_a))*(1+erro_a))}
Rpadrao sensor_a 0 1000
BestA estimativa_a 0 V={1/V(sensor_a)-2}
* Replica de bias com falhas permanentes em subpilares selecionados.
BdelayA atrasado_a 0 V={absdelay(V(estimativa_a),latencia)}
BdelayB atrasado_b 0 V={absdelay(V(estimativa_b),latencia)}
RlagA atrasado_a ajuste_a 1000
ClagA ajuste_a 0 {tau/1000} IC=0
RlagB atrasado_b ajuste_b 1000
ClagB ajuste_b 0 {tau/1000} IC=0
* As demandas sao correntes representadas numericamente por tensoes.
BdemandaA demanda_a 0 V={1u/escala*amortecimento*V(ajuste_a)*V(y)}
BdemandaB demanda_b 0 V={1u/escala*V(ajuste_b)}
Bganho ganho 0 V={min(1,orcamento_max/max(abs(V(demanda_a))+abs(V(demanda_b)),1p))}
BpedidoA pedido_a 0 V={absdelay(V(demanda_a)*V(ganho),atraso_coord)}
BpedidoB pedido_b 0 V={absdelay(V(demanda_b)*V(ganho),atraso_coord)}
Blimite limite 0 V={min(1,orcamento_max/max(abs(V(pedido_a))+abs(V(pedido_b)),1p))}
* politica 0: desligado; 1: 50 uA para cada canal; 2: reparticao proporcional.
Bcorrecao_a 0 y I={if(politica<0.5,0,if(politica<1.5,limit(V(demanda_a),-orcamento_max/2,orcamento_max/2),V(pedido_a)*V(limite)))}
Bcorrecao_b y 0 I={if(politica<0.5,0,if(politica<1.5,limit(V(demanda_b),-orcamento_max/2,orcamento_max/2),V(pedido_b)*V(limite)))}
Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))}
* Monitores didaticos: nao alimentam o controle.
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-9 abstol=1e-12

Bsub1 sub1 0 V={V(pert_b)+erro_b+if(falhas>=1,desvio_falha,0)}
Brank1 rank1 0 V={if(nsub>=2,if(V(sub2)<V(sub1),1,0),0)+if(nsub>=3,if(V(sub3)<V(sub1),1,0),0)+if(nsub>=4,if(V(sub4)<V(sub1),1,0),0)+if(nsub>=5,if(V(sub5)<V(sub1),1,0),0)+if(nsub>=6,if(V(sub6)<V(sub1),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub1),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub1),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub1),1,0),0)}
Bsub2 sub2 0 V={V(pert_b)+erro_b+if(falhas>=2,desvio_falha,0)}
Brank2 rank2 0 V={if(nsub>=1,if(V(sub1)<=V(sub2),1,0),0)+if(nsub>=3,if(V(sub3)<V(sub2),1,0),0)+if(nsub>=4,if(V(sub4)<V(sub2),1,0),0)+if(nsub>=5,if(V(sub5)<V(sub2),1,0),0)+if(nsub>=6,if(V(sub6)<V(sub2),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub2),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub2),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub2),1,0),0)}
Bsub3 sub3 0 V={V(pert_b)+erro_b+if(falhas>=3,desvio_falha,0)}
Brank3 rank3 0 V={if(nsub>=1,if(V(sub1)<=V(sub3),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub3),1,0),0)+if(nsub>=4,if(V(sub4)<V(sub3),1,0),0)+if(nsub>=5,if(V(sub5)<V(sub3),1,0),0)+if(nsub>=6,if(V(sub6)<V(sub3),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub3),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub3),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub3),1,0),0)}
Bsub4 sub4 0 V={V(pert_b)+erro_b+if(falhas>=4,desvio_falha,0)}
Brank4 rank4 0 V={if(nsub>=1,if(V(sub1)<=V(sub4),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub4),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub4),1,0),0)+if(nsub>=5,if(V(sub5)<V(sub4),1,0),0)+if(nsub>=6,if(V(sub6)<V(sub4),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub4),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub4),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub4),1,0),0)}
Bsub5 sub5 0 V={V(pert_b)+erro_b+if(falhas>=5,desvio_falha,0)}
Brank5 rank5 0 V={if(nsub>=1,if(V(sub1)<=V(sub5),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub5),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub5),1,0),0)+if(nsub>=4,if(V(sub4)<=V(sub5),1,0),0)+if(nsub>=6,if(V(sub6)<V(sub5),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub5),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub5),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub5),1,0),0)}
Bsub6 sub6 0 V={V(pert_b)+erro_b+if(falhas>=6,desvio_falha,0)}
Brank6 rank6 0 V={if(nsub>=1,if(V(sub1)<=V(sub6),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub6),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub6),1,0),0)+if(nsub>=4,if(V(sub4)<=V(sub6),1,0),0)+if(nsub>=5,if(V(sub5)<=V(sub6),1,0),0)+if(nsub>=7,if(V(sub7)<V(sub6),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub6),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub6),1,0),0)}
Bsub7 sub7 0 V={V(pert_b)+erro_b+if(falhas>=7,desvio_falha,0)}
Brank7 rank7 0 V={if(nsub>=1,if(V(sub1)<=V(sub7),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub7),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub7),1,0),0)+if(nsub>=4,if(V(sub4)<=V(sub7),1,0),0)+if(nsub>=5,if(V(sub5)<=V(sub7),1,0),0)+if(nsub>=6,if(V(sub6)<=V(sub7),1,0),0)+if(nsub>=8,if(V(sub8)<V(sub7),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub7),1,0),0)}
Bsub8 sub8 0 V={V(pert_b)+erro_b+if(falhas>=8,desvio_falha,0)}
Brank8 rank8 0 V={if(nsub>=1,if(V(sub1)<=V(sub8),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub8),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub8),1,0),0)+if(nsub>=4,if(V(sub4)<=V(sub8),1,0),0)+if(nsub>=5,if(V(sub5)<=V(sub8),1,0),0)+if(nsub>=6,if(V(sub6)<=V(sub8),1,0),0)+if(nsub>=7,if(V(sub7)<=V(sub8),1,0),0)+if(nsub>=9,if(V(sub9)<V(sub8),1,0),0)}
Bsub9 sub9 0 V={V(pert_b)+erro_b+if(falhas>=9,desvio_falha,0)}
Brank9 rank9 0 V={if(nsub>=1,if(V(sub1)<=V(sub9),1,0),0)+if(nsub>=2,if(V(sub2)<=V(sub9),1,0),0)+if(nsub>=3,if(V(sub3)<=V(sub9),1,0),0)+if(nsub>=4,if(V(sub4)<=V(sub9),1,0),0)+if(nsub>=5,if(V(sub5)<=V(sub9),1,0),0)+if(nsub>=6,if(V(sub6)<=V(sub9),1,0),0)+if(nsub>=7,if(V(sub7)<=V(sub9),1,0),0)+if(nsub>=8,if(V(sub8)<=V(sub9),1,0),0)}
BsensorB estimativa_b 0 V={if(nsub>=1,if(V(rank1)==floor(nsub/2),V(sub1),0),0)+if(nsub>=2,if(V(rank2)==floor(nsub/2),V(sub2),0),0)+if(nsub>=3,if(V(rank3)==floor(nsub/2),V(sub3),0),0)+if(nsub>=4,if(V(rank4)==floor(nsub/2),V(sub4),0),0)+if(nsub>=5,if(V(rank5)==floor(nsub/2),V(sub5),0),0)+if(nsub>=6,if(V(rank6)==floor(nsub/2),V(sub6),0),0)+if(nsub>=7,if(V(rank7)==floor(nsub/2),V(sub7),0),0)+if(nsub>=8,if(V(rank8)==floor(nsub/2),V(sub8),0),0)+if(nsub>=9,if(V(rank9)==floor(nsub/2),V(sub9),0),0)}
