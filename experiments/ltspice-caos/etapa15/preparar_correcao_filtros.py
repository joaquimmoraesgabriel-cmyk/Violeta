"""Isola os dois RCs da referencia para corresponder ao caminho da medida."""
from pathlib import Path
import json
from preparar_etapa15 import deck,SAVED

ROOT=Path(__file__).resolve().parent

def buffered(text):
    for label,ch in [('Y','y'),('D','d')]:
        old=f'Rexp{label} exp_{ch} exp_{ch}_f 1000'
        new=f'Bisol{label} exp_{ch}_buf 0 V={{V(exp_{ch})}}\nRexp{label} exp_{ch}_buf exp_{ch}_f 1000'
        assert text.count(old)==1
        text=text.replace(old,new)
    return text

def main():
    for source,target in [('MLC_circuito_reserva.inc','MLC_filtros_isolados.inc'),('MLC_ablacao.inc','MLC_ideal_filtros_isolados.inc')]:
        (ROOT/target).write_text(buffered((ROOT/source).read_text()),encoding='utf-8')
    specs=[(p,f) for p,f in [(1,0),(1,4),(3,0),(3,4),(3,2),(3,3)]]
    jobs=[]
    for p,f in specs:
        name=f'BUF_p{p}_f{f}'
        cases=json.loads((ROOT/f'EXP_p{p}_f{f}_d1.json').read_text())
        deck(ROOT,name,'MLC_filtros_isolados.inc',cases)
        path=ROOT/f'{name}.cir'
        path.write_text(path.read_text().replace('.tran 0',SAVED+'.tran 0',1),encoding='utf-8')
        jobs.append(name)
    name='BUF_ideal90'
    cases=json.loads((ROOT/'ABL_ideal_90.json').read_text())
    deck(ROOT,name,'MLC_ideal_filtros_isolados.inc',cases)
    path=ROOT/f'{name}.cir'
    path.write_text(path.read_text().replace('.tran 0',SAVED+'.tran 0',1),encoding='utf-8')
    jobs.append(name)
    (ROOT/'lotes_filtros.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    print('28 trajetorias: 24 com atuador nao ideal, 4 com ideal; limiares inalterados.')

if __name__=='__main__':main()
