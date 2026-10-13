"""Ablacao de tres canais: amortecimento, bias e amplitude da excitacao."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
def source(name,node,shift):
    p=[(0,(SEQ[0]>>shift)&1)]
    for i in range(1,17):p.extend([(i*.05,(SEQ[i-1]>>shift)&1),(i*.05+1e-6,(SEQ[i]>>shift)&1)])
    p.append((.85,(SEQ[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{t:.6f} {v}' for t,v in p)+')'
model=(ROOT.parent/'etapa7'/'MLC_coordenador.inc').read_text()
model=model.replace('forca*sin(omega*time/escala)','(forca+V(pert_c))*sin(omega*time/escala)')
model=model.replace('amortecimento*V(ajuste_a)*V(y)','amortecimento*V(ajuste_a)*V(y)*mod(topologia,2)')
model=model.replace('BdemandaB demanda_b 0 V={1u/escala*V(ajuste_b)}','BdemandaB demanda_b 0 V={1u/escala*V(ajuste_b)*mod(floor(topologia/2),2)}')
model=model.replace('abs(V(demanda_a))+abs(V(demanda_b))','abs(V(demanda_a))+abs(V(demanda_b))+abs(V(demanda_c))')
lines=[]
for line in model.splitlines():
    if line.startswith('Bcorrecao_a '):line='Bcorrecao_a 0 y I={V(demanda_a)*V(ganho)}'
    elif line.startswith('Bcorrecao_b '):line='Bcorrecao_b y 0 I={V(demanda_b)*V(ganho)}'
    elif line.startswith('Borcamento '):line='Borcamento orcamento 0 V={abs(I(Bcorrecao_a))+abs(I(Bcorrecao_b))+abs(I(Bcorrecao_c))}'
    lines.append(line)
lines += ['.param amp_c=if(perfil_c,0.012,0.004) erro_c=0.0002',
          'VdistC pert_c 0 SINE(0 {amp_c} 73 0 0 65)',
          'BsensorC estimativa_c 0 V={V(pert_c)+erro_c}',
          'BdelayC atrasado_c 0 V={absdelay(V(estimativa_c),latencia)}',
          'RlagC atrasado_c ajuste_c 1000','ClagC ajuste_c 0 {tau/1000} IC=0',
          'BdemandaC demanda_c 0 V={1u/escala*V(ajuste_c)*sin(omega*time/escala)*mod(floor(topologia/4),2)}',
          'Bcorrecao_c y 0 I={V(demanda_c)*V(ganho)}']
(ROOT/'MLC_tres_pilares.inc').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def deck(name,cases,demo=False):
    lines=['* Tres canais de atuacao: 100 uA compartilhados.','.include MLC_tres_pilares.inc',source('Va','entrada_a',1),source('Vb','entrada_b',0),'.param caso=0 perfil=0']
    for k in ['perfil_c','topologia','x_inicial','y_inicial','passo']:
        lines.append(f'.param {k}=table(caso,'+','.join(f'{i},{c[k]}' for i,c in enumerate(cases))+')')
    lines +=[f'.step param caso 0 {len(cases)-1} 1','.save V(x) V(saida) V(referencia) V(ler) V(orcamento)']
    if demo:lines+=['.save V(pert_a) V(pert_b) V(pert_c) V(ajuste_a) V(ajuste_b) V(ajuste_c) I(Bcorrecao_a) I(Bcorrecao_b) I(Bcorrecao_c)']
    lines+=['.tran 0 0.85 0 {passo} uic']
    for i in range(17):
        for label,op in [('minimo','MIN'),('maximo','MAX')]:lines.append(f'.meas tran {label}_{i:02} {op} V(x) FROM {i*.05+.03:.6f} TO {(i+1)*.05-.001:.6f}')
    lines+=['.meas tran pico_orcamento MAX V(orcamento) FROM 0 TO 0.85','.end','']
    (ROOT/(name+'.cir')).write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/(name+'.json')).write_text(json.dumps(cases,indent=2),encoding='utf-8')
cases=[dict(caso=i,perfil_c=p,topologia=top,x_inicial=x,y_inicial=-.2,passo=5e-6) for i,(p,top,x) in enumerate((p,top,x) for p in [0,1] for top in range(8) for x in [-.37,.37])]
deck('MLC_pilares_validacao',cases)
ref=[dict(c,caso=i,passo=2.5e-6) for i,c in enumerate(c for c in cases if c['topologia'] in [3,7])]
deck('MLC_pilares_refinamento',ref)
demo=[dict(c,caso=i) for i,c in enumerate(c for c in cases if c['perfil_c']==0 and c['topologia'] in [3,7] and c['x_inicial']==.37)]
deck('MLC_pilares_demo',demo,True)
print('32 trajetorias principais, 8 de refinamento, 2 de demonstracao.')
