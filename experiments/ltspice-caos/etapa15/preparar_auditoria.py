"""Repeticoes instrumentadas; nenhuma alteracao dos blocos ou limiares."""
from pathlib import Path
import json
from preparar_etapa15 import deck,SAVED

ROOT=Path(__file__).resolve().parent

def main():
    ideal=json.loads((ROOT/'ablacao_trajetorias.json').read_text())
    selected=next(t for t in ideal if t['arquivo']=='ABL_ideal_90' and t['alarme_indevido'])
    sources=[('AUD_circuito','EXP_p3_f0_d1',0,'MLC_circuito_reserva.inc'),
             ('AUD_ideal90','ABL_ideal_90',selected['caso'],'MLC_ablacao.inc')]
    jobs=[]
    for name,source,index,model in sources:
        case=dict(json.loads((ROOT/f'{source}.json').read_text())[index],caso=0)
        cases=[dict(case,caso=i,passo=step) for i,step in enumerate([1.25e-6,.625e-6])]
        deck(ROOT,name,model,cases)
        path=ROOT/f'{name}.cir'
        saves=SAVED+'\n.save V(filtro_y) V(filtro_d) V(exp_y) V(exp_d) V(obs_y_f) V(obs_d_f) V(exp_y_f) V(exp_d_f) V(obs_y) V(obs_d)\n'
        if name=='AUD_ideal90':saves+='.save I(xy:Bfeed) I(xd:Bfeed)\n'
        path.write_text(path.read_text().replace('.tran 0',saves+'.tran 0',1),encoding='utf-8')
        jobs.append(name)
    (ROOT/'lotes_auditoria.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    print('Quatro repeticoes instrumentadas: circuito/ideal e dois passos.')

if __name__=='__main__':main()
