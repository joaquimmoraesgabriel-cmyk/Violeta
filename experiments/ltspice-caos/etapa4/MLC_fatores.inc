* Mesma porta da revisao 2, com perturbacao variando no tempo.
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.005 bias=-0.005
.func g(z) {externo*z+(interno-externo)/2*(abs(z+1)-abs(z-1))}
.func pedida(e,z) {1u/escala*amortecimento*e*z}
Cx x 0 1u IC={x_inicial}
Cy y 0 1u IC={y_inicial}
Bx 0 x I={1u/escala*(V(y)-g(V(x)))}
By 0 y I={1u/escala*(-amortecimento*(1+V(perturbacao))*V(y)-V(x)+bias+entrada_amp*(2*V(entrada_a)-1+2*V(entrada_b)-1)+forca*sin(omega*time/escala))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
* Tres perturbacoes definidas antes da avaliacao, amplitude +/-0.5%.
Vlento lento 0 SINE(0 0.005 5)
Vdegrau degrau 0 PULSE(-0.005 0.005 35m 100u 100u 25m 50m)
Vrapido rapido 0 SINE(0 0.005 500)
Bpert perturbacao 0 V={if(perfil<0.5,V(lento),if(perfil<1.5,V(degrau),V(rapido)))}
* Replica dinamica equivalente a um resistor variavel.
Vprobe topo 0 1
Breplica topo sensor I={(V(topo)-V(sensor))/(1000*(1+V(perturbacao))*(1+erro_sensor))}
Rpadrao sensor 0 1000
Bestimativa estimativa 0 V={1/V(sensor)-2}
* Latencia pura e resposta de primeira ordem do sensor/controle.
Bdelay atrasado 0 V={absdelay(V(estimativa),latencia)}
Rlag atrasado filtrado 1000
Clag filtrado 0 {tau/1000} IC=0
Bajuste ajuste 0 V={if(modo<0.5,0,if(modo<1.5,V(estimativa),V(filtrado)))}
* modo 0: desligado; 1: ideal; 2: limitado; 3: mais lento e fraco.
Bcorrecao 0 y I={if(modo<0.5,0,if(modo<1.5,pedida(V(ajuste),V(y)),limit(pedida(V(ajuste),V(y)),-limite_corrente,limite_corrente)))}
Bsaturacao saturacao 0 V={if(modo>1.5,if(abs(pedida(V(ajuste),V(y)))>limite_corrente,1,0),0)}
Btracking tracking 0 V={V(ajuste)-V(perturbacao)}
.options plotwinsize=0 reltol=1e-5 vntol=1e-7 abstol=1e-10
