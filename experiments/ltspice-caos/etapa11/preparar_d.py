"""Candidato D: deriva multiplicativa da curva nao linear, compensacao no estado x."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
def source(name,node,shift):
    pairs=[(0,(SEQ[0]>>shift)&1)]
    for i in range(1,17):pairs.extend([(i*.05,(SEQ[i-1]>>shift)&1),(i*.05+1e-6,(SEQ[i]>>shift)&1)])
    pairs.append((.85,(SEQ[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{t:.6f} {v}' for t,v in pairs)+')'
BASE='''* MLC, quatro canais comportamentais; D corrige deriva da curva g(x).
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
* COORDENADOR_INICIO
Bganho ganho 0 V={min(1,orcamento_max/max(abs(V(demanda_a))+abs(V(demanda_b))+abs(V(demanda_c))+abs(V(demanda_d)),1p))}
Bcorrecao_a 0 y I={V(demanda_a)*V(ganho)}
Bcorrecao_b y 0 I={V(demanda_b)*V(ganho)}
Bcorrecao_c y 0 I={V(demanda_c)*V(ganho)}
Bcorrecao_d 0 x I={V(demanda_d)*V(ganho)}
* COORDENADOR_FIM
Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))+abs(I(Bcorrecao_c))+abs(I(Bcorrecao_d))}
Bsaida saida 0 V={if(V(x)>0,1,0)}
Breferencia referencia 0 V={if(V(entrada_a)>0.5,if(V(entrada_b)>0.5,1,0),0)}
Bler ler 0 V={if(mod(time,50m)>=30m,if(mod(time,50m)<49m,1,0),0)}
.options plotwinsize=0 reltol=1e-6 vntol=1e-9 abstol=1e-12
'''
def deck(root,name,model,cases,extra=False):
    root.mkdir(exist_ok=True)
    lines=['* '+name,f'.include {model}',source('Va','entrada_a',1),source('Vb','entrada_b',0),'.param caso=0']
    for key in cases[0]:
        if key in ['caso','nome_perfil']:continue
        lines.append(f'.param {key}=table(caso,'+','.join(f'{i},{c[key]}' for i,c in enumerate(cases))+')')
    lines+=[f'.step param caso 0 {len(cases)-1} 1','.save V(x) V(saida) V(orcamento)']
    if extra:lines+=['.save V(y) V(pert_d) V(ajuste_d) V(referencia) V(ler) I(Bcorrecao_a) I(Bcorrecao_b) I(Bcorrecao_c) I(Bcorrecao_d)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for i in range(17):
        for label,op in [('minimo','MIN'),('maximo','MAX')]:lines.append(f'.meas tran {label}_{i:02} {op} V(x) FROM {i*.05+.03:.6f} TO {(i+1)*.05-.001:.6f}')
    lines+=['.meas tran pico_orcamento MAX V(orcamento) FROM 0 TO 0.85']
    if 'politica_coord' in cases[0]:
        lines.insert(lines.index('.tran 0 0.85 0 {passo} uic'),'.save V(sem_protecao) V(guard_ativo) V(reserva_ativa) V(sobra) V(falta)')
        lines+=['.meas tran pico_sem_protecao MAX V(sem_protecao) FROM 0 TO 0.85','.meas tran uso_protecao AVG V(guard_ativo) FROM 0 TO 0.85','.meas tran uso_reserva AVG V(reserva_ativa) FROM 0 TO 0.85','.meas tran sobra MAX V(sobra) FROM 0.03 TO 0.85','.meas tran falta MAX V(falta) FROM 0.03 TO 0.85']
    lines+=['.end','']
    (root/(name+'.cir')).write_text('\n'.join(lines),encoding='utf-8')
    (root/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')
def main():
    ROOT.mkdir(exist_ok=True)
    (ROOT/'MLC_quatro_pilares.inc').write_text(BASE,encoding='utf-8')
    profiles=[('D_isolado_moderado',0,0,0,.004,[0,8]),('quatro_desvios',.0025,.003,.002,.004,[7,15]),('D_isolado_forte',0,0,0,.010,[0,8])]
    cases=[]
    for p,(name,a,b,c,d,tops) in enumerate(profiles):
        for top in tops:
            for step in [2.5e-6,1.25e-6]:
                for x in [-.37,.37]:cases.append(dict(caso=len(cases),perfil=p,nome_perfil=name,topologia=top,amp_a=a,amp_b=b,amp_c=c,amp_d=d,x_inicial=x,y_inicial=-.2,passo=step))
    deck(ROOT,'MLC_D_validacao','MLC_quatro_pilares.inc',cases)
    demo=[dict(c,caso=i) for i,c in enumerate(c for c in cases if c['perfil']==2 and c['x_inicial']==.37 and c['passo']==2.5e-6)]
    deck(ROOT,'MLC_D_demo','MLC_quatro_pilares.inc',demo,True)
    print('Pilar D preparado: 24 trajetorias principais e 2 de demonstracao.')
if __name__=='__main__':main()
