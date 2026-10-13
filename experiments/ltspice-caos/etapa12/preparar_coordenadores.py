"""Comparacao predefinida de alocacao, falhas e reserva; sensores continuos iguais."""
from pathlib import Path
import sys,json,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import BASE,deck
COORD='''* Grupos AB e CD: demandas representadas numericamente em ampere.
Bg1 pedido_grupo1 0 V={abs(V(demanda_a))+abs(V(demanda_b))}
Bg2 pedido_grupo2 0 V={abs(V(demanda_c))+abs(V(demanda_d))}
Btotal pedido_total 0 V={V(pedido_grupo1)+V(pedido_grupo2)}
Bglobal ganho_comum 0 V={min(1,orcamento_max/max(V(pedido_total),1p))}
* Politica 2: emprestimo informado por demandas de 50 us atras.
Bquota1 quota1 0 V={orcamento_max/2+max(0,orcamento_max/2-absdelay(V(pedido_grupo2),50u))}
Bquota2 quota2 0 V={orcamento_max/2+max(0,orcamento_max/2-absdelay(V(pedido_grupo1),50u))}
Blocal1 ganho1 0 V={min(1,if(politica_coord==2,V(quota1),orcamento_max/2)/max(V(pedido_grupo1),1p))}
Blocal2 ganho2 0 V={min(1,if(politica_coord==2,V(quota2),orcamento_max/2)/max(V(pedido_grupo2),1p))}
* Politica 3: ordem fixa B,D,A,C, sem acesso a resposta AND esperada.
BpriB prioridade_b 0 V={limit(V(demanda_b),-orcamento_max,orcamento_max)}
BrestB resta_b 0 V={max(0,orcamento_max-abs(V(prioridade_b)))}
BpriD prioridade_d 0 V={limit(V(demanda_d),-V(resta_b),V(resta_b))}
BrestD resta_d 0 V={max(0,V(resta_b)-abs(V(prioridade_d)))}
BpriA prioridade_a 0 V={limit(V(demanda_a),-V(resta_d),V(resta_d))}
BrestA resta_a 0 V={max(0,V(resta_d)-abs(V(prioridade_a)))}
BpriC prioridade_c 0 V={limit(V(demanda_c),-V(resta_a),V(resta_a))}
* Falhas fisicas injetadas: 1 silencio/perda de heartbeat; 2 atraso; 3 sinal invertido.
.func janela(t) {if(t>=0.24335,if(t<0.30335,1,0),0)}
Bfalha falha_injetada 0 V={janela(time)}
Bmult1 multiplicador1 0 V={if(V(falha_injetada)>0.5,if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
Bmult2 multiplicador2 0 V={if(politica_coord==1,1,if(politica_coord==2,1,V(multiplicador1)))}
* O atraso de 500 us e permanente no ensaio 2; evitar atraso variavel nao causal.
BbaseA base_a 0 V={if(politica_coord==3,V(prioridade_a),V(demanda_a)*if(politica_coord==1,V(ganho1),if(politica_coord==2,V(ganho1),V(ganho_comum))))}
BbaseB base_b 0 V={if(politica_coord==3,V(prioridade_b),V(demanda_b)*if(politica_coord==1,V(ganho1),if(politica_coord==2,V(ganho1),V(ganho_comum))))}
BbaseC base_c 0 V={if(politica_coord==3,V(prioridade_c),V(demanda_c)*if(politica_coord==1,V(ganho2),if(politica_coord==2,V(ganho2),V(ganho_comum))))}
BbaseD base_d 0 V={if(politica_coord==3,V(prioridade_d),V(demanda_d)*if(politica_coord==1,V(ganho2),if(politica_coord==2,V(ganho2),V(ganho_comum))))}
BpreA pre_a 0 V={absdelay(V(base_a),if(falha_coord==2,500u,0))*V(multiplicador1)}
BpreB pre_b 0 V={absdelay(V(base_b),if(falha_coord==2,500u,0))*V(multiplicador1)}
BpreC pre_c 0 V={absdelay(V(base_c),if(falha_coord==2,500u,0))*V(multiplicador2)}
BpreD pre_d 0 V={absdelay(V(base_d),if(falha_coord==2,500u,0))*V(multiplicador2)}
Bpretotal sem_protecao 0 V={abs(V(pre_a))+abs(V(pre_b))+abs(V(pre_c))+abs(V(pre_d))}
* Watchdog observa heartbeat e sinais de comandos; nao le a identidade da falha.
Vpulse relogio 0 PULSE(0 1 0 0.1u 0.1u 100u 200u)
Bheartbeat heartbeat 0 V={V(relogio)*if(V(falha_injetada)>0.5,if(falha_coord==1,0,1),1)}
Bcharge 0 saude I={max(V(heartbeat)-V(saude),0)/10000}
Csaude saude 0 1n IC=1
Rsaude saude 0 500k
Binval invalido 0 V={if(V(pre_a)*V(demanda_a)<-1e-18,1,if(V(pre_b)*V(demanda_b)<-1e-18,1,if(V(pre_c)*V(demanda_c)<-1e-18,1,if(V(pre_d)*V(demanda_d)<-1e-18,1,0))))}
BchargeE 0 alerta I={max(V(invalido)-V(alerta),0)/10000}
Calerta alerta 0 1n IC=0
Ralerta alerta 0 500k
Breserva reserva_ativa 0 V={if(politica_coord==4,if(V(saude)<0.3,1,if(V(alerta)>0.3,1,0)),0)}
* Reserva simples: 25 uA por canal; usa a propria demanda filtrada atual.
BcmdA comando_a 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_a),-orcamento_max/4,orcamento_max/4),V(pre_a))}
BcmdB comando_b 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_b),-orcamento_max/4,orcamento_max/4),V(pre_b))}
BcmdC comando_c 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_c),-orcamento_max/4,orcamento_max/4),V(pre_c))}
BcmdD comando_d 0 V={if(V(reserva_ativa)>0.5,limit(V(demanda_d),-orcamento_max/4,orcamento_max/4),V(pre_d))}
* Protecao comum a TODAS as politicas: rejeita sinal oposto ao pedido atual e limita soma.
BokA ok_a 0 V={if(V(comando_a)*V(demanda_a)<-1e-18,0,V(comando_a))}
BokB ok_b 0 V={if(V(comando_b)*V(demanda_b)<-1e-18,0,V(comando_b))}
BokC ok_c 0 V={if(V(comando_c)*V(demanda_c)<-1e-18,0,V(comando_c))}
BokD ok_d 0 V={if(V(comando_d)*V(demanda_d)<-1e-18,0,V(comando_d))}
Bguard ganho_guard 0 V={min(1,orcamento_max/max(abs(V(ok_a))+abs(V(ok_b))+abs(V(ok_c))+abs(V(ok_d)),1p))}
Bguardflag guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(invalido)>0.5,1,0))}
Bcorrecao_a 0 y I={V(ok_a)*V(ganho_guard)}
Bcorrecao_b y 0 I={V(ok_b)*V(ganho_guard)}
Bcorrecao_c y 0 I={V(ok_c)*V(ganho_guard)}
Bcorrecao_d 0 x I={V(ok_d)*V(ganho_guard)}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}
'''
def main():
    ROOT.mkdir(exist_ok=True)
    model=re.sub(r'\* COORDENADOR_INICIO.*?\* COORDENADOR_FIM',COORD,BASE,flags=re.S)+'\n.options threads=1\n'
    (ROOT/'MLC_coordenadores.inc').write_text(model,encoding='utf-8')
    # Janela de falha declarada antes dos ensaios de falha: inclui 11 e 01.
    faultmodel=model.replace('t>=0.24335','t>=0.34335').replace('t<0.30335','t<0.40335')
    (ROOT/'MLC_coordenadores_falhas.inc').write_text(faultmodel,encoding='utf-8')
    profiles=[('equilibrado',.0025,.003,.002,.004),('AB_exige_mais',.0015,.010,.001,.001),('CD_exige_mais',.0005,.001,.005,.008),('todos_exigem',.006,.009,.007,.008)]
    cases=[]
    for p,(name,a,b,c,d) in enumerate(profiles):
        for policy in range(5):
            for step in [2.5e-6,1.25e-6]:
                for x in [-.37,.37]:cases.append(dict(caso=len(cases),perfil=p,nome_perfil=name,topologia=15,politica_coord=policy,falha_coord=0,amp_a=a,amp_b=b,amp_c=c,amp_d=d,x_inicial=x,y_inicial=-.2,passo=step))
    # Quatro lotes independentes por perfil para evitar um unico arquivo gigante.
    jobs=[]
    for p in range(4):
        group=[dict(c,caso=i) for i,c in enumerate(c for c in cases if c['perfil']==p)]
        name=f'COORD_perfil{p}';deck(ROOT,name,'MLC_coordenadores.inc',group);jobs.append(name)
    faultcases=[]
    for fault in [1,2,3]:
        for policy in range(5):
            for x in [-.37,.37]:faultcases.append(dict(caso=len(faultcases),perfil=1,nome_perfil='AB_exige_mais',topologia=15,politica_coord=policy,falha_coord=fault,amp_a=.0015,amp_b=.010,amp_c=.001,amp_d=.001,x_inicial=x,y_inicial=-.2,passo=2.5e-6))
    for fault in [1,2,3]:
        group=[dict(c,caso=i) for i,c in enumerate(c for c in faultcases if c['falha_coord']==fault)]
        name=f'COORD_falha{fault}';deck(ROOT,name,'MLC_coordenadores_falhas.inc',group);jobs.append(name)
    silent=[dict(c,caso=i,falha_coord=4,perfil=0,nome_perfil='equilibrado',amp_a=.0025,amp_b=.003,amp_c=.002,amp_d=.004) for i,c in enumerate(c for c in faultcases if c['falha_coord']==1)]
    deck(ROOT,'COORD_falha4','MLC_coordenadores_falhas.inc',silent)
    (ROOT/'lote_falha_silenciosa.json').write_text(json.dumps(['COORD_falha4']),encoding='utf-8')
    silent_ab=[dict(c,caso=i,falha_coord=4) for i,c in enumerate(c for c in faultcases if c['falha_coord']==1)]
    deck(ROOT,'COORD_falha4_AB','MLC_coordenadores_falhas.inc',silent_ab)
    (ROOT/'lote_falha_silenciosa_AB.json').write_text(json.dumps(['COORD_falha4_AB']),encoding='utf-8')
    (ROOT/'lotes.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    print('Preparados 80 sem falha, 40 de falhas no perfil AB e 10 de falha silenciosa equilibrada.')
if __name__=='__main__':main()
