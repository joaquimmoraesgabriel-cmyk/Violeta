* Modelo comportamental das equacoes MLC, Murali et al. arXiv:1811.10029.
* x,y sao estados normalizados representados por tensoes; nao e montagem fisica.
.param escala=100u amortecimento=1.015 externo=-0.55 interno=-1.02
.param forca=0.11 omega=0.74 entrada_amp=0.002 bias=-0.002
.func g(z) {externo*z+(interno-externo)/2*(abs(z+1)-abs(z-1))}
Cx x 0 1u IC={x_inicial}
Cy y 0 1u IC={y_inicial}
Bx 0 x I={1u/escala*(V(y)-g(V(x)))}
By 0 y I={1u/escala*(-amortecimento*(1+desvio)*V(y)-V(x)+bias+entrada_amp*(2*V(entrada_a)-1+2*V(entrada_b)-1)+forca*sin(omega*time/escala))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
.options plotwinsize=0 reltol=1e-5 vntol=1e-7 abstol=1e-10
.save V(x) V(y) V(entrada_a) V(entrada_b) V(saida)
