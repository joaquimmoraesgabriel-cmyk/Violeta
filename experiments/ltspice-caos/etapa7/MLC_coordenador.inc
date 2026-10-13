* Porta MLC, dois canais e uma camada de alocacao de corrente.
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.param latencia=50u tau=100u erro_a=0.0002 erro_b=-0.0002 orcamento_max=100u
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
BsensorB estimativa_b 0 V={V(pert_b)+erro_b}
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
* politica 0: desligado; 1: 50 uA para cada canal; 2: reparticao proporcional.
Bcorrecao_a 0 y I={if(politica<0.5,0,if(politica<1.5,limit(V(demanda_a),-orcamento_max/2,orcamento_max/2),V(demanda_a)*V(ganho)))}
Bcorrecao_b y 0 I={if(politica<0.5,0,if(politica<1.5,limit(V(demanda_b),-orcamento_max/2,orcamento_max/2),V(demanda_b)*V(ganho)))}
Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))}
* Monitores didaticos: nao alimentam o controle.
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-9 abstol=1e-12
