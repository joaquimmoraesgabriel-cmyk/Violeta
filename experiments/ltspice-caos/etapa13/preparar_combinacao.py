"""Alternativa: combinar demandas no mesmo estado ANTES de dois atuadores fisicos."""
from pathlib import Path
import sys,json,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import BASE,deck
NET='''* Dois atuadores reais no modelo: um em y para A/B/C, outro em x para D.
BpedidoY pedido_y 0 V={V(demanda_a)-V(demanda_b)-V(demanda_c)}
BpedidoT pedido_total 0 V={abs(V(pedido_y))+abs(V(demanda_d))}
Bganho ganho 0 V={min(1,orcamento_max/max(V(pedido_total),1p))}
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bmult multiplicador 0 V={if(janela(time),if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(pedido_y)*V(ganho),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreD pre_d 0 V={absdelay(V(demanda_d)*V(ganho),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreT sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
BokY ok_y 0 V={if(V(pre_y)*V(pedido_y)<-1e-18,0,V(pre_y))}
BokD ok_d 0 V={if(V(pre_d)*V(demanda_d)<-1e-18,0,V(pre_d))}
Bguard ganho_guard 0 V={min(1,orcamento_max/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
BguardF guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(pre_y)*V(pedido_y)<-1e-18,1,if(V(pre_d)*V(demanda_d)<-1e-18,1,0)))}
Breserva reserva_ativa 0 V=0
Batuador_y 0 y I={V(ok_y)*V(ganho_guard)}
Batuador_x 0 x I={V(ok_d)*V(ganho_guard)}
'''
def main():
    ROOT.mkdir(exist_ok=True)
    model=re.sub(r'\* COORDENADOR_INICIO.*?\* COORDENADOR_FIM',NET,BASE,flags=re.S)
    model=model.replace('Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))+abs(I(Bcorrecao_c))+abs(I(Bcorrecao_d))}', 'Borcamento orcamento 0 V={abs(I(Batuador_y))+abs(I(Batuador_x))}')
    model=model.replace('vntol=1e-9','vntol=1e-11')+'\n.options threads=1\nBfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}\nBsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}\n'
    (ROOT/'MLC_combinado.inc').write_text(model,encoding='utf-8')
    common=(ROOT.parent/'etapa12'/'MLC_coordenadores.inc').read_text().replace('vntol=1e-9','vntol=1e-11')
    (ROOT/'MLC_comum_mesma_precisao.inc').write_text(common,encoding='utf-8')
    cases=[]
    for profile in [0,3]:
        source=json.loads((ROOT.parent/'etapa12'/f'COORD_perfil{profile}.json').read_text())
        cases.extend(c for c in source if c['politica_coord']==0)
    commoncases=[dict(c,caso=i) for i,c in enumerate(cases)]
    netcases=[dict(c,caso=i,politica_coord=5) for i,c in enumerate(cases)]
    deck(ROOT,'COMB_comum','MLC_comum_mesma_precisao.inc',commoncases)
    deck(ROOT,'COMB_combinado','MLC_combinado.inc',netcases)
    faults=[]
    for f in [1,2,3,4]:
        source=json.loads((ROOT.parent/'etapa12'/('COORD_falha4_AB.json' if f==4 else f'COORD_falha{f}.json')).read_text())
        faults.extend(c for c in source if c['politica_coord']==0)
    faults=[dict(c,caso=i,politica_coord=5) for i,c in enumerate(faults)]
    deck(ROOT,'COMB_falhas','MLC_combinado.inc',faults)
    (ROOT/'lotes.json').write_text(json.dumps(['COMB_comum','COMB_combinado','COMB_falhas']),encoding='utf-8')
    print('16 trajetorias pareadas sem falha e 8 de falha; mesmo vntol=1e-11.')
if __name__=='__main__':main()

