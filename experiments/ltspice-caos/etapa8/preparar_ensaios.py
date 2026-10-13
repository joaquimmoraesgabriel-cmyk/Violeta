"""Ensaios previamente definidos de atraso, capacidade e redundancia de sensores."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'etapa7'
sys.path.insert(0,str(BASE))
# Nao importar preparar_etapa7: o modulo escreve os arquivos da etapa anterior.
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
def source(name,node,shift):
    pairs=[(0,(SEQ[0]>>shift)&1)]
    for i in range(1,len(SEQ)):
        pairs.extend([(i*.05,(SEQ[i-1]>>shift)&1),(i*.05+1e-6,(SEQ[i]>>shift)&1)])
    pairs.append((.85,(SEQ[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+ ' '.join(f'{t:.6f} {v}' for t,v in pairs)+')'
def deck(name,model,cases,extra=False):
    lines=['* '+name,f'.include {model}',source('Va','entrada_a',1),source('Vb','entrada_b',0),'.param caso=0']
    keys=[k for k in cases[0] if k!='caso']
    for k in keys:
        lines.append(f'.param {k}=table(caso,'+','.join(f'{i},{c[k]}' for i,c in enumerate(cases))+')')
    lines+= [f'.step param caso 0 {len(cases)-1} 1','.save V(x) V(saida) V(referencia) V(ler) V(orcamento)']
    if extra: lines+=['.save V(estimativa_b) V(sub1) V(sub2) V(sub3) V(ajuste_b)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for i in range(17):
        for label,op,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)'),('positivo','AVG','V(saida)')]:
            lines.append(f'.meas tran {label}_{i:02} {op} {trace} FROM {i*.05+.03:.6f} TO {(i+1)*.05-.001:.6f}')
    lines+=['.meas tran pico_orcamento MAX V(orcamento) FROM 0 TO 0.85','.end','']
    (ROOT/(name+'.cir')).write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')

base=(BASE/'MLC_coordenador.inc').read_text()
base=base.replace('erro_b=-0.0002 orcamento_max=100u','erro_b=-0.0002')
base=base.replace('* politica 0:', '''BpedidoA pedido_a 0 V={absdelay(V(demanda_a)*V(ganho),atraso_coord)}
BpedidoB pedido_b 0 V={absdelay(V(demanda_b)*V(ganho),atraso_coord)}
Blimite limite 0 V={min(1,orcamento_max/max(abs(V(pedido_a))+abs(V(pedido_b)),1p))}
* politica 0:''')
base=base.replace('V(demanda_a)*V(ganho)))}','V(pedido_a)*V(limite)))}').replace('V(demanda_b)*V(ganho)))}','V(pedido_b)*V(limite)))}')
(ROOT/'MLC_limites.inc').write_text(base,encoding='utf-8')
cases=[]
for budget in [50e-6,100e-6,200e-6]:
    for policy,delay in [(1,0),(2,0),(2,100e-6),(2,500e-6),(2,1e-3)]:
        for x in [-.37,.37]:
            cases.append(dict(caso=len(cases),perfil=1,politica=policy,atraso_coord=delay,orcamento_max=budget,x_inicial=x,y_inicial=-.2,passo=5e-6))
deck('MLC_limites_validacao','MLC_limites.inc',cases)
ref=[dict(c,caso=i,passo=2.5e-6) for i,c in enumerate(c for c in cases if c['orcamento_max']==100e-6 and c['politica']==2 and c['atraso_coord'] in [0,100e-6,1e-3])]
deck('MLC_limites_refinamento','MLC_limites.inc',ref)

# Interpretacao parcial: subpilares sao replicas de medicao de UM parametro.
# Sao nove fontes distintas e um voto por mediana, sem conhecer a saida AND.
redund=base.replace('BsensorB estimativa_b 0 V={V(pert_b)+erro_b}', '* Replica de bias com falhas permanentes em subpilares selecionados.')
lines=[]
for i in range(1,10):
    lines.append(f'Bsub{i} sub{i} 0 V={{V(pert_b)+erro_b+if(falhas>={i},desvio_falha,0)}}')
    terms=[]
    for j in range(1,10):
        if i==j: continue
        # Desempate por indice para valores identicos.
        op='<=' if j<i else '<'
        terms.append(f'if(nsub>={j},if(V(sub{j}){op}V(sub{i}),1,0),0)')
    lines.append(f'Brank{i} rank{i} 0 V={{'+'+'.join(terms)+'}')
terms=[f'if(nsub>={i},if(V(rank{i})==floor(nsub/2),V(sub{i}),0),0)' for i in range(1,10)]
lines.append('BsensorB estimativa_b 0 V={'+'+'.join(terms)+'}')
redund+='\n'+'\n'.join(lines)+'\n'
(ROOT/'MLC_subpilares.inc').write_text(redund,encoding='utf-8')
cases=[]
for n in [1,3,9]:
    for f in sorted(set([0,1,2,4,n])):
        # Evitar comparar rotulos de falha impossiveis para uma rede pequena.
        if f>n: continue
        for x in [-.37,.37]:
            cases.append(dict(caso=len(cases),perfil=1,politica=2,atraso_coord=0,orcamento_max=100e-6,x_inicial=x,y_inicial=-.2,passo=5e-6,nsub=n,falhas=f,desvio_falha=.02))
deck('MLC_subpilares_validacao','MLC_subpilares.inc',cases)
ref=[dict(c,caso=i,passo=2.5e-6) for i,c in enumerate(c for c in cases if c['falhas'] in [1,2])]
deck('MLC_subpilares_refinamento','MLC_subpilares.inc',ref)
demo=[dict(c,caso=i) for i,c in enumerate(c for c in cases if c['falhas']==1 and c['x_inicial']==.37)]
deck('MLC_subpilares_demo','MLC_subpilares.inc',demo,True)
print('Preparados: limites 30+6, redundancia 22+10, demonstracao 3 trajetorias.')
