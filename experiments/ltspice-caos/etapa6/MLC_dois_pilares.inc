* Porta MLC da revisao 2: duas perturbacoes distintas e dois canais.
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.param latencia=50u tau=100u erro_a=0.0002 erro_b=-0.0002
.param ligado_a=mod(topologia,2) ligado_b=floor(topologia/2)
* Mesmo orcamento total: um canal tem 100 uA; dois tem 50 uA cada.
.param limite_a=if(topologia>2.5,50u,100u) limite_b=if(topologia>2.5,50u,100u)
.func g(z) {externo*z+(interno-externo)/2*(abs(z+1)-abs(z-1))}
Cx x 0 1u IC={x_inicial}
Cy y 0 1u IC={y_inicial}
Bx 0 x I={1u/escala*(V(y)-g(V(x)))}
By 0 y I={1u/escala*(-amortecimento*(1+V(pert_a))*V(y)-V(x)+bias+V(pert_b)+entrada_amp*(2*V(entrada_a)-1+2*V(entrada_b)-1)+forca*sin(omega*time/escala))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
* perfil 0: so amortecimento; 1: so bias; 2: ambas.
Va_dist onda_a 0 SINE(0 0.005 500)
Vb_dist onda_b 0 SINE(0 0.006 137 0 0 40)
BpertA pert_a 0 V={if(perfil<0.5,V(onda_a),if(perfil<1.5,0,V(onda_a)))}
BpertB pert_b 0 V={if(perfil<0.5,0,V(onda_b))}
* Canal A: replica resistiva do amortecimento, como nos ensaios anteriores.
Vprobe topo 0 1
Breplica topo sensor_a I={(V(topo)-V(sensor_a))/(1000*(1+V(pert_a))*(1+erro_a))}
Rpadrao sensor_a 0 1000
BestA estimativa_a 0 V={1/V(sensor_a)-2}
* Canal B: replica ideal do desvio de bias, com erro aditivo.
BsensorB estimativa_b 0 V={V(pert_b)+erro_b}
BdelayA atrasado_a 0 V={absdelay(V(estimativa_a),latencia)}
BdelayB atrasado_b 0 V={absdelay(V(estimativa_b),latencia)}
RlagA atrasado_a ajuste_a 1000
ClagA ajuste_a 0 {tau/1000} IC=0
RlagB atrasado_b ajuste_b 1000
ClagB ajuste_b 0 {tau/1000} IC=0
* A injeta uma compensacao proporcional a y; B retira o desvio de bias.
Bcorrecao_a 0 y I={ligado_a*limit(1u/escala*amortecimento*V(ajuste_a)*V(y),-limite_a,limite_a)}
Bcorrecao_b y 0 I={ligado_b*limit(1u/escala*V(ajuste_b),-limite_b,limite_b)}
Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))}
Bsaturado_a saturado_a 0 V={ligado_a*if(abs(1u/escala*amortecimento*V(ajuste_a)*V(y))>limite_a,1,0)}
Bsaturado_b saturado_b 0 V={ligado_b*if(abs(1u/escala*V(ajuste_b))>limite_b,1,0)}
.options plotwinsize=0 reltol=1e-5 vntol=1e-7 abstol=1e-10
