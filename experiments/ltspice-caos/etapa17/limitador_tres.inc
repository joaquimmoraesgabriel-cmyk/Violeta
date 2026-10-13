.subckt LIMITADOR3 iy ix ie vp vm ganho
Bsum soma 0 V={(abs(V(iy))+abs(V(ix))+abs(V(ie)))*r_sense}
Vref ref 0 {margem_limite*r_sense}
Bexcesso excesso 0 V={max(V(soma)-V(ref),0)}
Xlim excesso 0 vp vm limite level2 Avol={avol_limit} GBW={gbw_limit} Slew=100Meg Ilimit=1m Rail=0.2 Rin=1G
Bganho ganho 0 V={1/(1+max(V(limite),0))}
.ends LIMITADOR3
