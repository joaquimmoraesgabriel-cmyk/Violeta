"""Etapa 17: um unico dono das cotas, comum ou dois grupos ABC / D+E."""
from pathlib import Path
import json, shutil, sys

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'etapa16'
sys.path.insert(0,str(OLD))
from preparar_etapa16 import SAVED,SAVE_E
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import deck

ALLOCATION='''* Coordenador de recursos associado a E: cotas normalizadas, soma unica.
* arquitetura=0 proporcional comum; 1 grupos fixos; 2 grupos com emprestimo.
* A/B/C sao combinados ANTES da alocacao, preservando cancelamentos assinados.
BfracCom frac_com 0 V={abs(V(demanda_y))/max(V(pedido_total),1p)}
BfracGrp frac_grp 0 V={limit(0.5+(max(0,cap_operacao/2-abs(V(demanda_d)))-max(0,cap_operacao/2-abs(V(demanda_y))))/cap_operacao,0,1)}
BfracAlvo frac_alvo 0 V={if(arquitetura==0,V(frac_com),if(arquitetura==1,0.5,V(frac_grp)))}
Btransporte frac_atrasada 0 V={absdelay(V(frac_alvo),lat_coord)}
Rquota frac_atrasada frac_filtro 1000
Cquota frac_filtro 0 {tau_coord/1000} IC=0.5
* Falhas do supervisor: 1 queda com heartbeat; 2 atraso extra; 3 duplo gasto; 4 cota valida enviesada.
Bfracao frac_recebida 0 V={absdelay(V(frac_filtro),if(falha_super==2,500u,0))}
BmodoQ modo_quota 0 V={if(janela(time),falha_super,0)}
BqY q_msg_y 0 V={if(V(modo_quota)==1,0,if(V(modo_quota)==3,cap_operacao,if(V(modo_quota)==4,0,cap_operacao*V(frac_recebida))))}
BqD q_msg_d 0 V={if(V(modo_quota)==1,0,if(V(modo_quota)==3,cap_operacao,if(V(modo_quota)==4,cap_operacao,cap_operacao*(1-V(frac_recebida)))))}
BhbQ hb_quota 0 V={if(falha_super==1,1-janela(time),1)}
* Validador nao recebe codigo/horario da falha: heartbeat, faixa e soma das mensagens.
BqInval quota_invalida 0 V={if(V(hb_quota)<0.5,1,if(min(V(q_msg_y),V(q_msg_d))<-1n,1,if(V(q_msg_y)+V(q_msg_d)>cap_operacao+1n,1,0)))}
BquotaY quota_y 0 V={if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_y),0,cap_operacao))}
BquotaD quota_d 0 V={if(V(quota_invalida)>0.5,cap_operacao/2,limit(V(q_msg_d),0,cap_operacao))}
BbaseY base_y 0 V={sgn(V(demanda_y))*min(abs(V(demanda_y)),V(quota_y))}
BbaseD base_d 0 V={sgn(V(demanda_d))*min(abs(V(demanda_d)),V(quota_d))}
* E mantem reserva local de ate 5 uA. A arbitragem final debita E de Y quando necessario.
* Nao ha um segundo pedido ao topo nem uma segunda concessao da mesma corrente.
Bdeficit deficit_d 0 V={max(0,abs(V(demanda_e))-abs(V(base_d))-1u)}
BesperadoE esperado_e 0 V={if(abs(V(demanda_d))>abs(V(base_d))+1u,if(V(demanda_e)*V(demanda_d)>0,sgn(V(demanda_e))*min(cap_e,min(V(deficit_d),max(0,cap_operacao-abs(V(base_d))))),0),0)}
BesperadoY esperado_y 0 V={sgn(V(base_y))*min(abs(V(base_y)),max(0,cap_operacao-abs(V(base_d))-abs(V(esperado_e))))}
BesperadoD esperado_d 0 V={V(base_d)}
Bsaldo saldo_concedido 0 V={cap_operacao-abs(V(esperado_y))-abs(V(esperado_d))-abs(V(esperado_e))}
'''

SAVE_COORD='''.save V(quota_y) V(quota_d) V(q_msg_y) V(q_msg_d) V(quota_invalida) V(hb_quota)
.save V(frac_alvo) V(frac_recebida) V(base_y) V(saldo_concedido)
'''

def models():
    ROOT.mkdir(exist_ok=True)
    for f in ['atuadores_etapa14.inc','UniversalOpAmp2.lib','limitador_tres.inc','executar.ps1','estado_lotes.py']:
        shutil.copyfile(OLD/f,ROOT/f)
    base=(OLD/'MLC_pilar_E_v2.inc').read_text(encoding='utf-8')
    begin=base.index('* modo_e=1:')
    end=base.index('* Somente este bloco injeta falha.',begin)
    base=base[:begin]+ALLOCATION+base[end:]
    # alvo_topo: 0 coordenador comum (ambos); 1 so grupo ABC; 2 so grupo D.
    for ch,target in [('Y',1),('D',2)]:
        old=f'Bpre{ch} pre_{ch.lower()} 0 V={{absdelay(V(esperado_{ch.lower()}),if(falha_coord==2,500u,0))*V(multiplicador)}}'
        new=f'Bpre{ch} pre_{ch.lower()} 0 V={{absdelay(V(esperado_{ch.lower()}),if(alvo_topo=={3-target},0,if(falha_coord==2,500u,0)))*if(alvo_topo=={3-target},1,V(multiplicador))}}'
        assert old in base
        base=base.replace(old,new)
    (ROOT/'MLC_coordenador_E.inc').write_text(base,encoding='utf-8')

def make(name,architecture=0,fault=0,steps=(1.25e-6,.625e-6),**params):
    originals=json.loads((OLD/'E_cota5_f0.json').read_text(encoding='utf-8'))[:2]
    cases=[]
    for step in steps:
        for c in originals:
            c=dict(c,caso=len(cases),passo=step,falha_coord=fault,arquitetura=architecture,
                   lat_coord=20e-6,tau_coord=50e-6,falha_super=0,alvo_topo=0)
            c.update(params);cases.append(c)
    deck(ROOT,name,'MLC_coordenador_E.inc',cases)
    p=ROOT/f'{name}.cir'
    p.write_text(p.read_text(encoding='utf-8').replace('.tran 0',SAVED+SAVE_E+SAVE_COORD+'.tran 0',1),encoding='utf-8')
    return name

def manifest(name,jobs):
    (ROOT/name).write_text(json.dumps(jobs,indent=2),encoding='utf-8')

if __name__=='__main__':
    models()
    manifest('lotes_piloto.json',[
        make('C_comum_f0'),make('G_fixo_f0',1),make('G_emprestimo_f0',2),
        make('G_sem_atuacao_E',2,cap_e=0)])
    print('Preparadas 16 trajetorias: comum, dois grupos fixos, dois grupos com emprestimo, ablacao E.')
