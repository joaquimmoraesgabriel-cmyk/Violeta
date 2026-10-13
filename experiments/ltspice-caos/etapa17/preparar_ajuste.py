"""Ajuste motivado pelo piloto: projecao L2 dos pedidos antes da prioridade E."""
from preparar_etapa17 import ROOT,make,manifest

def revised_model():
    model=(ROOT/'MLC_coordenador_E.inc').read_text(encoding='utf-8')
    old='BfracAlvo frac_alvo 0 V={if(arquitetura==0,V(frac_com),if(arquitetura==1,0.5,V(frac_grp)))}'
    new='''* Projecao no orcamento L1: minimiza erro quadratico dos dois pedidos estimados.
* A reserva E ainda modifica a solucao em ate 5 uA depois desta projecao.
BfracL2 frac_l2 0 V={if(V(pedido_total)<=cap_operacao,V(frac_com),limit(0.5+(abs(V(demanda_y))-abs(V(demanda_d)))/(2*cap_operacao),0,1))}
BfracAlvo frac_alvo 0 V={V(frac_l2)}'''
    assert old in model
    model=model.replace(old,new).replace('absdelay(V(frac_filtro),if(falha_super==2,500u,0))',
        'absdelay(if(ideal_coord,V(frac_alvo),V(frac_filtro)),if(falha_super==2,500u,0))')
    (ROOT/'MLC_coordenador_E_l2.inc').write_text(model,encoding='utf-8')

if __name__=='__main__':
    revised_model()
    jobs=[]
    for label,ideal in [('L2_filtrado',0),('L2_instantaneo',1)]:
        jobs.append(make(label,3,ideal_coord=ideal))
        p=ROOT/f'{label}.cir'
        p.write_text(p.read_text(encoding='utf-8').replace('.include MLC_coordenador_E.inc','.include MLC_coordenador_E_l2.inc'),encoding='utf-8')
    manifest('lotes_ajuste.json',jobs)
    print('Ajuste exploratorio: 8 trajetorias saudaveis, filtrado e limite ideal instantaneo.')
