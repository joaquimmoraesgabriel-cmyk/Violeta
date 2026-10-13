* Somente para separar capacidade de dinamica do atuador/limitador.
* Preserva o RC de comando, partida, shunt e todos os blocos de controle.
.subckt ATUADOR cmd out vp vm medido habilitado
Bfeed 0 entrada_shunt I={if(V(habilitado)>0.5,V(cmd),0)}
Rshunt entrada_shunt out 1000
Bmed medido 0 V={V(entrada_shunt,out)/1000}
.ends ATUADOR
