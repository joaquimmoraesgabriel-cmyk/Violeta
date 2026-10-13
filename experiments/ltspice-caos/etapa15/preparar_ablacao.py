"""Seguimento controlado: atuacao ideal com o mesmo RC, 90 versus 100 uA."""
from pathlib import Path
import json
from preparar_etapa15 import deck, SAVED

ROOT=Path(__file__).resolve().parent

def main():
    core=(ROOT/'MLC_circuito_reserva.inc').read_text()
    core=core.replace('.include atuadores_etapa14.inc','.include atuador_ideal_ablacao.inc')
    core=core.replace('XL med_y med_d vp vm ganho_fisico LIMITADOR','VganhoIdeal ganho_fisico 0 1')
    (ROOT/'MLC_ablacao.inc').write_text(core,encoding='utf-8')
    (ROOT/'atuador_ideal_ablacao.inc').write_text('''* Somente para separar capacidade de dinamica do atuador/limitador.
* Preserva o RC de comando, partida, shunt e todos os blocos de controle.
.subckt ATUADOR cmd out vp vm medido habilitado
Bfeed 0 entrada_shunt I={if(V(habilitado)>0.5,V(cmd),0)}
Rshunt entrada_shunt out 1000
Bmed medido 0 V={V(entrada_shunt,out)/1000}
.ends ATUADOR
''',encoding='utf-8')
    originals=json.loads((ROOT/'EXP_p3_f0_d1.json').read_text())
    jobs=[]
    for cap in [90,100]:
        cases=[dict(c,caso=i,cap_operacao=cap*1e-6,hardware=0) for i,c in enumerate(originals)]
        name=f'ABL_ideal_{cap}'
        deck(ROOT,name,'MLC_ablacao.inc',cases)
        path=ROOT/f'{name}.cir'
        path.write_text(path.read_text().replace('.tran 0',SAVED+'.tran 0',1),encoding='utf-8')
        jobs.append(name)
    (ROOT/'lotes_ablacao.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    print('Ablacao: 8 trajetorias em alta demanda saudavel; mesmo RC, capacidades 90/100 uA.')

if __name__=='__main__':main()
