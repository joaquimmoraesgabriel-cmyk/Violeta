* Segunda candidata: isolamento de saida na energizacao, controlado por RC.
.include UniversalOpAmp2.lib
.param r_sense=1000 avol=1e6 gbw_drive=2Meg slew_drive=10Meg vos_drive=0 avol_limit=10000
.subckt ATUADOR cmd out vp vm medido habilitado params: erro_r=0
Bset set 0 V={V(cmd)*r_sense}
Bfeedback feedback 0 V={V(driver,out)}
Xamp set feedback vp vm driver level2 Avol={avol} GBW={gbw_drive} Slew={slew_drive} Ilimit=1m Rail=0.2 Vos={vos_drive} Rin=1G
Siso driver entrada_shunt habilitado 0 ISO
Rshunt entrada_shunt out {r_sense*(1+erro_r)}
Bmed medido 0 V={V(entrada_shunt,out)/r_sense}
.model ISO SW(Ron=0.1 Roff=1T Vt=0.5 Vh=0.05)
.ends ATUADOR
.subckt LIMITADOR iy ix vp vm ganho
Bsum soma 0 V={(abs(V(iy))+abs(V(ix)))*r_sense}
Vref ref 0 {margem_limite*r_sense}
Bexcesso excesso 0 V={max(V(soma)-V(ref),0)}
Xlim excesso 0 vp vm limite level2 Avol={avol_limit} GBW={gbw_limit} Slew=100Meg Ilimit=1m Rail=0.2 Rin=1G
Bganho ganho 0 V={1/(1+max(V(limite),0))}
.ends LIMITADOR
