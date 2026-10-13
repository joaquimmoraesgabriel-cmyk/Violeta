"""Extensao predefinida do circuito da etapa 14, sem reajuste do detector."""
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa11'))
from preparar_d import deck

SAVED = '''.save V(y) V(referencia) V(ler) V(reserva_ativa) V(trip) V(timer) V(discrepancia) V(limiar)
.save V(esperado_y) V(esperado_d) V(med_y) V(med_d) V(comando_y) V(comando_d) V(ganho_fisico) V(habilitado)
.save V(xy:entrada_shunt) V(xd:entrada_shunt) V(br_y) V(br_d) I(XY:Rshunt) I(XD:Rshunt) I(Vsensey) I(Vsensed)
'''

def main():
    ROOT.mkdir(exist_ok=True)
    old = ROOT.parent / 'etapa14'
    for file in ['MLC_circuito_reserva.inc', 'atuadores_etapa14.inc', 'UniversalOpAmp2.lib', 'executar.ps1']:
        shutil.copyfile(old / file, ROOT / file)
    jobs = []
    # Saudavel e silencio em quatro perfis. Atraso/inversao em AB e alta demanda.
    # Parada sem heartbeat em AB. O detector nao utiliza heartbeat.
    pairs = [(p, f) for p in range(4) for f in [0, 4]]
    pairs += [(p, f) for p in [1, 3] for f in [2, 3]] + [(1, 1)]
    specs = [(p, f, 1, [1.25e-6, .625e-6]) for p, f in pairs]
    specs += [(p, f, 0, [1.25e-6]) for p in [1, 3] for f in [4, 2, 3]]
    for profile, fault, detector, steps in specs:
        originals = json.loads((ROOT.parent / 'etapa13' / f'SOMA_combinados_perfil{profile}.json').read_text())
        seeds = [c for c in originals if c['passo'] == 1.25e-6]
        cases = [dict(c, caso=i, passo=step, detector=detector, falha_coord=fault,
                      cap_operacao=90e-6, hardware=1)
                 for i, (step, c) in enumerate((s, c) for s in steps for c in seeds)]
        name = f'EXP_p{profile}_f{fault}_d{detector}'
        deck(ROOT, name, 'MLC_circuito_reserva.inc', cases)
        path = ROOT / f'{name}.cir'
        text = path.read_text().replace('.tran 0', SAVED + '.tran 0', 1)
        path.write_text(text, encoding='utf-8')
        jobs.append(name)
    # Cada trabalhador fica com decks completos; resultados antigos nao sao sobrescritos.
    (ROOT / 'lotes.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    print(f'{len(jobs)} decks, 64 trajetorias, 1088 janelas; 52 protegidas e 12 referencias.')

if __name__ == '__main__':
    main()
