"""Etapa 18: supervisao de idade/coerencia, reserva local e latencia L2."""
from pathlib import Path
import json, shutil, sys
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'etapa17'
sys.path.insert(0,str(ROOT.parent/'etapa16'))
from preparar_etapa16 import SAVED, SAVE_E
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import deck

MONITOR='''* MONITOR INDEPENDENTE: usa mensagens, demandas medidas e relogio local.
* Independencia funcional, nao de sensores, alimentacao ou tecnologia.
BqRefCom q_ref_com 0 V={abs(V(demanda_y))/max(abs(V(demanda_y))+abs(V(demanda_d)),1p)}
BqRefL2 q_ref_l2 0 V={if(abs(V(demanda_y))+abs(V(demanda_d))<=cap_operacao,V(q_ref_com),limit(0.5+(abs(V(demanda_y))-abs(V(demanda_d)))/(2*cap_operacao),0,1))}
BqRef q_ref_alvo 0 V={if(politica_l2,V(q_ref_l2),V(q_ref_com))}
BqRefDelay q_ref_atrasada 0 V={absdelay(V(q_ref_alvo),lat_coord+lat_ref_extra)}
RqRef q_ref_atrasada q_ref_filtro 1000
CqRef q_ref_filtro 0 {tau_coord*(1+tol_ref)/1000} IC=0.5
* Buffers: o observador nao carrega o RC da referencia.
BqExpY q_exp_y 0 V={escala_med*cap_operacao*V(q_ref_filtro)}
BqExpD q_exp_d 0 V={escala_med*cap_operacao*(1-V(q_ref_filtro))}
BqObsY q_obs_y 0 V={escala_med*(V(q_msg_y)+offset_q+ruido_q*sin(2*pi*13007*time))}
BqObsD q_obs_d 0 V={escala_med*(V(q_msg_d)-offset_q+ruido_q*sin(2*pi*17011*time+0.7))}
RqEY q_exp_y q_exp_y_f 1000
CqEY q_exp_y_f 0 4n IC=0
RqED q_exp_d q_exp_d_f 1000
CqED q_exp_d_f 0 4n IC=0
RqOY q_obs_y q_obs_y_f 1000
CqOY q_obs_y_f 0 4n IC=0
RqOD q_obs_d q_obs_d_f 1000
CqOD q_obs_d_f 0 4n IC=0
BqErro erro_cota 0 V={(abs(V(q_obs_y_f)-V(q_exp_y_f))+abs(V(q_obs_d_f)-V(q_exp_d_f)))/escala_med}
BqLimiar limiar_cota 0 V={2u+0.05*cap_operacao}
BqCoer incoerente 0 V={if(V(erro_cota)>V(limiar_cota),1,0)}
BclockRx clock_rx 0 V={time*(1+drift_ppm*1e-6)+clock_offset}
BqAge idade_cota 0 V={V(clock_rx)-V(stamp_rx)}
BqVelha idade_invalida 0 V={if(V(idade_cota)>80u,1,if(V(idade_cota)<-30u,1,0))}
BqRazao razao_cota 0 V={if(time>2m,max(V(quota_invalida),max(V(incoerente),V(idade_invalida))),0)}
CqTimer timer_cota 0 1n IC=0
BqTimer 0 timer_cota I={if(V(razao_cota)>0.5,(1-V(timer_cota))/(20u/1n),-V(timer_cota)/(40u/1n))}
BqTrip trip_cota 0 V={if(V(timer_cota)>0.7,1,0)}
CqMem memoria_cota 0 1n IC=0
BqMem 0 memoria_cota I={max(V(trip_cota)-V(memoria_cota),0)/1000}
RqMem memoria_cota 0 1T
BqReserva reserva_cota 0 V={if(diagnostico_cotas,if(V(memoria_cota)>0.5,1,0),0)}
* FIM MONITOR. Reserva proporcional local; guard antigo permanece durante confirmacao.
BquotaY quota_y 0 V={if(V(reserva_cota)>0.5,cap_operacao*V(q_ref_com),if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_y),0,cap_operacao)))}
BquotaD quota_d 0 V={if(V(reserva_cota)>0.5,cap_operacao*(1-V(q_ref_com)),if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_d),0,cap_operacao)))}
'''

SAVE_Q='''.save V(quota_y) V(quota_d) V(q_msg_y) V(q_msg_d) V(quota_invalida)
.save V(idade_cota) V(idade_invalida) V(erro_cota) V(incoerente) V(trip_cota) V(reserva_cota)
.save V(timer_cota) V(saldo_concedido)
'''

def models():
    for f in ['atuadores_etapa14.inc','UniversalOpAmp2.lib','limitador_tres.inc','executar.ps1','estado_lotes.py']:
        shutil.copyfile(OLD/f,ROOT/f)
    text=(OLD/'MLC_coordenador_E.inc').read_text(encoding='utf-8')
    a=text.index('BfracAlvo '); b=text.index('Btransporte ',a)
    text=text[:a]+'''BfracL2 frac_l2 0 V={if(V(pedido_total)<=cap_operacao,V(frac_com),limit(0.5+(abs(V(demanda_y))-abs(V(demanda_d)))/(2*cap_operacao),0,1))}
BfracAlvo frac_alvo 0 V={if(politica_l2,V(frac_l2),V(frac_com))}
'''+text[b:]
    text=text.replace('if(falha_super==2,500u,0)', 'if(falha_super==2,500u,if(falha_super==5,500u,0))')
    text=text.replace('0,cap_operacao*V(frac_recebida))))}', '0,if(V(modo_quota)==6,limit(cap_operacao*V(frac_recebida)+12u,0,cap_operacao),cap_operacao*V(frac_recebida)))))}')
    text=text.replace('cap_operacao,cap_operacao*(1-V(frac_recebida)))))}', 'cap_operacao,if(V(modo_quota)==6,cap_operacao-limit(cap_operacao*V(frac_recebida)+12u,0,cap_operacao),cap_operacao*(1-V(frac_recebida))))))}')
    a=text.index('* Validador nao recebe')
    text=text[:a]+'''* Metadados injetados apenas aqui: falha 2 atrasa valor e marca; 5 so valor.
BstampTx stamp_tx 0 V={time}
BstampRx stamp_rx 0 V={absdelay(V(stamp_tx),lat_coord+if(falha_super==2,500u,0))}
'''+text[a:]
    a=text.index('BquotaY ');b=text.index('BbaseY ',a)
    text=text[:a]+MONITOR+text[b:]
    for forbidden in ['falha_', 'janela(', 'V(pert_', 'V(referencia)', 'V(frac_alvo)', 'V(frac_filtro)']:
        assert forbidden not in MONITOR, forbidden
    for line in text.splitlines():
        if not line.startswith('*'):assert line.count('(')==line.count(')'),line
    (ROOT/'MLC_cotas_v1.inc').write_text(text,encoding='utf-8')

def make(name,steps=(1.25e-6,.625e-6),**params):
    originals=json.loads((OLD/'C_comum_f0.json').read_text(encoding='utf-8'))[:2]
    cases=[]
    for step in steps:
        for original in originals:
            c=dict(original,caso=len(cases),passo=step,politica_l2=0,diagnostico_cotas=1,
                   lat_ref_extra=2e-6,tol_ref=.05,offset_q=.5e-6,ruido_q=.5e-6,
                   drift_ppm=0,clock_offset=0)
            c.update(params);cases.append(c)
    deck(ROOT,name,'MLC_cotas_v1.inc',cases)
    p=ROOT/f'{name}.cir'
    p.write_text(p.read_text(encoding='utf-8').replace('.tran 0',SAVED+SAVE_E+SAVE_Q+'.tran 0',1),encoding='utf-8')
    return name

def main():
    models()
    pilot=[make('C_sadio_on'),make('C_sadio_off',diagnostico_cotas=0),
           make('C_vies_on',falha_super=4),make('C_vies_off',falha_super=4,diagnostico_cotas=0),
           make('C_atraso_on',falha_super=2),
           make('L2_5_10',politica_l2=1,lat_coord=5e-6,tau_coord=10e-6),
           make('L2_1_2',politica_l2=1,lat_coord=1e-6,tau_coord=2e-6)]
    fine=(.625e-6,)
    extra=[make('C_queda_on',fine,falha_super=1),make('C_duplo_on',fine,falha_super=3),
           make('C_replay_on',falha_super=5),
           make('C_tolerancia_mais',fine,tol_ref=.2,lat_ref_extra=5e-6,clock_offset=10e-6,drift_ppm=25,ruido_q=1e-6),
           make('C_vies12_on',fine,falha_super=6),make('C_dupla_falha',fine,falha_super=4,falha_coord=4),
           make('R_C',(.3125e-6,)),make('R_L2_5_10',(.3125e-6,),politica_l2=1,lat_coord=5e-6,tau_coord=10e-6),
           make('C_tolerancia_menos',fine,tol_ref=-.2,lat_ref_extra=-5e-6,clock_offset=-10e-6,drift_ppm=-25,ruido_q=1e-6)]
    for name,jobs in [('lotes_piloto.json',pilot),('lotes_expansao.json',extra)]:
        (ROOT/name).write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    smoke=make('SMOKE',fine)
    p=ROOT/f'{smoke}.cir'
    p.write_text(p.read_text(encoding='utf-8').replace('.tran 0 0.85 ','.tran 0 0.001 '),encoding='utf-8')
    print('Preparadas 48 trajetorias completas + 2 casos curtos de inicializacao.')

if __name__=='__main__':main()
