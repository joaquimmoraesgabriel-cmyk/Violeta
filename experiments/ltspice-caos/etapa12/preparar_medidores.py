"""Conferencia independente do monitor B: correntes salvas e sondas de 0 V."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa11'))
from preparar_d import deck
cases=[dict(c,caso=i) for i,c in enumerate(json.loads((ROOT/'COORD_falha4_AB.json').read_text())[:2])]
jobs=[]
for probe,tight in [(False,False),(True,False),(False,True),(True,True)]:
    model=(ROOT/'MLC_coordenadores_falhas.inc').read_text()
    if tight:model=model.replace('vntol=1e-9','vntol=1e-11')
    if probe:
        model=model.replace('Bcorrecao_a 0 y I=','Bcorrecao_a 0 mede_a I=').replace('Bcorrecao_b y 0 I=','Bcorrecao_b mede_b 0 I=').replace('Bcorrecao_c y 0 I=','Bcorrecao_c mede_c 0 I=').replace('Bcorrecao_d 0 x I=','Bcorrecao_d 0 mede_d I=')
        model+='\nVsenseA mede_a y 0\nVsenseB y mede_b 0\nVsenseC y mede_c 0\nVsenseD mede_d x 0\nBreal real 0 V={abs(I(VsenseA))+abs(I(VsenseB))+abs(I(VsenseC))+abs(I(VsenseD))}\n'
    name=('COORD_medidor_sondas' if probe else 'COORD_medidor_direto')+('_preciso' if tight else '')
    jobs.append(name)
    (ROOT/(name+'.inc')).write_text(model,encoding='utf-8')
    deck(ROOT,name,name+'.inc',cases)
    text=(ROOT/(name+'.cir')).read_text()
    saves='.save I(Bcorrecao_a) I(Bcorrecao_b) I(Bcorrecao_c) I(Bcorrecao_d) V(ganho_guard) V(ok_a) V(ok_b) V(ok_c) V(ok_d)'
    if probe:saves+=' I(VsenseA) I(VsenseB) I(VsenseC) I(VsenseD) V(real)'
    text=text.replace('.tran 0',saves+'\n.tran 0',1)
    if probe:text=text.replace('.end','.meas tran pico_sondas MAX V(real) FROM 0 TO 0.85\n.end')
    (ROOT/(name+'.cir')).write_text(text,encoding='utf-8')
(ROOT/'lote_medidores.json').write_text(json.dumps(jobs),encoding='utf-8')
print('Oito trajetorias: correntes salvas e sondas de 0 V, duas precisões e dois estados iniciais.')
