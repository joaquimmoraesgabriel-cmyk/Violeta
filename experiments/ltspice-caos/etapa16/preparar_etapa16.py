"""Experimentos registrados antes das simulacoes; E local com capacidade contabilizada."""
from pathlib import Path
import json, shutil, sys

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'etapa15'
sys.path.insert(0, str(ROOT.parent / 'etapa11'))
from preparar_d import deck

SAVED = '''.save V(y) V(referencia) V(ler) V(reserva_ativa) V(trip) V(timer) V(discrepancia) V(limiar)
.save V(esperado_y) V(esperado_d) V(med_y) V(med_d) V(comando_y) V(comando_d) V(ganho_fisico) V(habilitado)
.save V(xy:entrada_shunt) V(xd:entrada_shunt) V(br_y) V(br_d) I(XY:Rshunt) I(XD:Rshunt) I(Vsensey) I(Vsensed)
.save V(demanda_y) V(demanda_d) V(ajuste_d) V(pert_d)
'''
SAVE_E = '''.save V(esperado_e) V(med_e) V(comando_e) V(xe:entrada_shunt) V(br_e) I(XE:Rshunt) I(Vsensee)
.save V(ajuste_e) V(estimativa_e) V(deficit_d) V(base_d)
'''

def sensors_e():
    # Nove replicas favoraveis, continuamente ativas. Erro comum nao e eliminado.
    out = ['* Nove sensores E e mediana exata por ordenacao; nao e o seletor adaptativo da etapa 9.']
    nodes = []
    for i in range(9):
        n = f'e_sensor{i}'
        offset = (i-4)*.000002
        bad = 'if(falhas_e>='+str(i+1)+',0.02,0)' if i < 5 else '0'
        out.append(f'BEs{i} {n} 0 V={{V(pert_d)+erro_d+({offset})+erro_comum_e+({bad})}}')
        nodes.append(n)
    # Odd-even transposition sort: nove passes ordenam nove entradas.
    for p in range(9):
        for i in range(p % 2, 8, 2):
            lo, hi = f'e_sort{p}_{i}', f'e_sort{p}_{i+1}'
            out.extend([f'BElo{p}_{i} {lo} 0 V={{min(V({nodes[i]}),V({nodes[i+1]}))}}',
                        f'BEhi{p}_{i} {hi} 0 V={{max(V({nodes[i]}),V({nodes[i+1]}))}}'])
            nodes[i], nodes[i+1] = lo, hi
    out += [f'BEmed estimativa_e 0 V={{V({nodes[4]})}}',
            'BEdelay atrasado_e 0 V={absdelay(V(estimativa_e),latencia)}',
            'RElag atrasado_e ajuste_e 1000', 'CElag ajuste_e 0 {tau/1000} IC=0',
            'BdemandaE demanda_e 0 V={1u/escala*V(ajuste_e)*g(V(x))}']
    return '\n'.join(out)+'\n'

def models():
    ROOT.mkdir(exist_ok=True)
    for f in ['atuadores_etapa14.inc','UniversalOpAmp2.lib','executar.ps1']:
        shutil.copyfile(OLD/f, ROOT/f)
    base = (OLD/'MLC_filtros_isolados.inc').read_text(encoding='utf-8')
    base = base.replace('latencia=50u tau=100u erro_a=0.0002 erro_b=-0.0002 erro_c=0.0002 erro_d=0.00002',
                        'latencia={lat_s} tau={tau_s} erro_a={0.0002*esc_erro} erro_b={-0.0002*esc_erro} erro_c={0.0002*esc_erro} erro_d={0.00002*esc_erro}')
    (ROOT/'MLC_referencia.inc').write_text(base, encoding='utf-8')
    original = '''Blocal ganho_local 0 V={min(1,cap_operacao/max(V(pedido_total),1p))}
BesperadoY esperado_y 0 V={V(demanda_y)*V(ganho_local)}
BesperadoD esperado_d 0 V={V(demanda_d)*V(ganho_local)}'''
    assert original in base
    allocation = '''* modo_e=1: reserva fixa; modo_e=2: reserva liberada/retirada de Y sob saturacao de D.
* E recebe somente o pedido e a cota local de D. Nao recebe comando ou falha do topo.
Blocal ganho_local 0 V={min(1,(cap_operacao-if(modo_e==1,cap_e,0))/max(V(pedido_total),1p))}
BbaseD base_d 0 V={V(demanda_d)*V(ganho_local)}
Bdeficit deficit_d 0 V={max(0,abs(V(demanda_e))-abs(V(base_d))-1u)}
BesperadoE esperado_e 0 V={if(abs(V(demanda_d))>abs(V(base_d))+1u,if(V(demanda_e)*V(demanda_d)>0,sgn(V(demanda_e))*min(cap_e,V(deficit_d)),0),0)}
BesperadoY esperado_y 0 V={if(modo_e==1,V(demanda_y)*V(ganho_local),sgn(V(demanda_y))*min(abs(V(demanda_y)*V(ganho_local)),max(0,cap_operacao-abs(V(base_d))-abs(V(esperado_e)))))}
BesperadoD esperado_d 0 V={V(base_d)}'''
    e = base.replace(original, sensors_e()+allocation)
    e = e.replace('cap_operacao/max(abs(V(ok_y))+abs(V(ok_d)),1p)',
                  'max(0,cap_operacao-abs(V(esperado_e)))/max(abs(V(ok_y))+abs(V(ok_d)),1p)')
    e = e.replace('BcmdD comando_d 0 V={V(ok_d)*V(ganho_guard)}',
                  'BcmdD comando_d 0 V={V(ok_d)*V(ganho_guard)}\nBcmdE comando_e 0 V={V(esperado_e)}')
    e = e.replace('XL med_y med_d vp vm ganho_fisico LIMITADOR', '''BnormE norm_e 0 V={escala_med*V(comando_e)}
RcmdE norm_e filtro_e 1000
CcmdE filtro_e 0 {tau_cmd/1000} IC=0
BphyE phy_e 0 V={V(filtro_e)/escala_med*V(ganho_fisico)}
XE phy_e br_e vp vm med_e habilitado ATUADOR
Vsensee br_e x 0
.include limitador_tres.inc
XL med_y med_d med_e vp vm ganho_fisico LIMITADOR3''')
    e = e.replace('Borcamento orcamento 0 V={abs(V(med_y))+abs(V(med_d))}',
                  'Borcamento orcamento 0 V={abs(V(med_y))+abs(V(med_d))+abs(V(med_e))}')
    (ROOT/'MLC_pilar_E.inc').write_text(e, encoding='utf-8')
    limiter=(OLD/'atuadores_etapa14.inc').read_text(encoding='utf-8').split('.subckt LIMITADOR',1)[1]
    limiter='.subckt LIMITADOR'+limiter
    limiter=limiter.replace('LIMITADOR iy ix vp vm ganho','LIMITADOR3 iy ix ie vp vm ganho').replace('abs(V(ix)))','abs(V(ix))+abs(V(ie)))').replace('.ends LIMITADOR','.ends LIMITADOR3')
    (ROOT/'limitador_tres.inc').write_text(limiter, encoding='utf-8')
    # Controle de alocacao: mesma prioridade a D, somente dois atuadores; todo D passa pelo topo.
    priority = base.replace(original,sensors_e()+allocation.replace('BesperadoD esperado_d 0 V={V(base_d)}',
                                    'BesperadoD esperado_d 0 V={V(base_d)+V(esperado_e)}'))
    (ROOT/'MLC_prioridade_D.inc').write_text(priority, encoding='utf-8')

def revised_models():
    # Nao sobrescreve os modelos ja carregados pelos lotes piloto.
    for old,new in [('MLC_pilar_E.inc','MLC_pilar_E_v2.inc'),('MLC_prioridade_D.inc','MLC_prioridade_D_v2.inc')]:
        text=(ROOT/old).read_text(encoding='utf-8')
        assert 'min(cap_e,V(deficit_d))' in text
        text=text.replace('min(cap_e,V(deficit_d))','min(cap_e,min(V(deficit_d),max(0,cap_operacao-abs(V(base_d)))))')
        (ROOT/new).write_text('* Revisao: E respeita tambem a cota ja comprometida com D.\n'+text,encoding='utf-8')

def make(name, model='MLC_referencia.inc', fault=0, steps=(1.25e-6,.625e-6), **params):
    originals=json.loads((OLD/'BUF_p3_f0.json').read_text(encoding='utf-8'))[:2]
    cases=[]
    for s in steps:
        for c in originals:
            c=dict(c, caso=len(cases), passo=s, falha_coord=fault, lat_s=50e-6,tau_s=100e-6,
                   esc_erro=1,modo_e=2,cap_e=20e-6,falhas_e=0,erro_comum_e=0)
            c.update(params)
            cases.append(c)
    deck(ROOT,name,model,cases)
    path=ROOT/f'{name}.cir'
    saved=SAVED+(SAVE_E if model.startswith('MLC_pilar_E') else '')
    if model.startswith('MLC_prioridade_D'):saved+='.save V(ajuste_e) V(estimativa_e) V(esperado_e) V(base_d) V(deficit_d)\n'
    path.write_text(path.read_text(encoding='utf-8').replace('.tran 0',saved+'.tran 0',1),encoding='utf-8')
    return name

def main():
    models()
    jobs=[make('E_fixo_f0','MLC_pilar_E.inc',modo_e=1),make('E_livre_f0','MLC_pilar_E.inc'),
          make('D_prioridade_f0','MLC_prioridade_D.inc'),make('S_sem_offset',esc_erro=0),
          make('S_rapido',lat_s=5e-6,tau_s=10e-6),make('S_rapido_sem_offset',lat_s=5e-6,tau_s=10e-6,esc_erro=0)]
    (ROOT/'lotes_piloto.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    print('Piloto: 24 trajetorias em seis decks; os controles historicos serao reanalisados dos RAW originais.')

if __name__=='__main__':main()
