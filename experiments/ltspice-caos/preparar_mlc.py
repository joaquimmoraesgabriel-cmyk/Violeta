"""Gera ensaios LTspice definidos antes da avaliacao de robustez."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SEQUENCE = [0, 0, 1, 0, 2, 0, 3, 1, 1, 2, 1, 3, 2, 2, 3, 3, 0]
SLOT = 0.05
assert len(set(zip(SEQUENCE, SEQUENCE[1:]))) == 16


def source(name, node, shift):
    pairs = [('0', str((SEQUENCE[0] >> shift) & 1))]
    for index in range(1, len(SEQUENCE)):
        pairs.extend([
            (f'{index*SLOT:.6f}', str((SEQUENCE[index-1] >> shift) & 1)),
            (f'{index*SLOT+1e-6:.6f}', str((SEQUENCE[index] >> shift) & 1)),
        ])
    pairs.append((f'{len(SEQUENCE)*SLOT:.6f}', str((SEQUENCE[-1] >> shift) & 1)))
    return f'{name} {node} 0 PWL(' + ' '.join(' '.join(pair) for pair in pairs) + ')'


def make_deck(title, steps):
    lines = [title, '.include MLC_base.inc', source('Va', 'entrada_a', 1), source('Vb', 'entrada_b', 0)]
    declarations='\n'.join(steps)
    defaults={'desvio':'0','x_inicial':'0','y_inicial':'0','passo':'5u'}
    for name,value in defaults.items():
        if not re.search(rf'\b{name}=|\.step param {name}\b', declarations):
            lines.append(f'.param {name}={value}')
    lines += steps
    lines += [f'.tran 0 {len(SEQUENCE)*SLOT:.6f} 0 {{passo}} uic']
    for index, code in enumerate(SEQUENCE):
        start, end = index*SLOT+0.030, (index+1)*SLOT-0.001
        lines += [
            f'* Janela {index:02}: A={code//2}, B={code%2}; descarta transicao.',
            f'.meas tran media_{index:02} AVG V(x) FROM {start:.6f} TO {end:.6f}',
            f'.meas tran minimo_{index:02} MIN V(x) FROM {start:.6f} TO {end:.6f}',
            f'.meas tran maximo_{index:02} MAX V(x) FROM {start:.6f} TO {end:.6f}',
            f'.meas tran positivo_{index:02} AVG V(saida) FROM {start:.6f} TO {end:.6f}',
        ]
    return '\n'.join(lines + ['.end', ''])


(ROOT / 'MLC_AND_sequencia.cir').write_text(make_deck(
    '* MLC: AND por sinal persistente de x; sequencia com todas as 16 transicoes.', []), encoding='utf-8')
(ROOT / 'MLC_AND_validacao.cir').write_text(make_deck(
    '* MLC: validacao independente; 3 estados x 3 desvios x 2 passos.', [
        '.step param x_inicial list -1 0 1',
        '.step param desvio list -0.005 0 0.005',
        '.step param passo list 5u 2.5u',
    ]), encoding='utf-8')
print('Arquivos de sequencia e validacao preparados: 16 transicoes, 17 janelas por execucao.')

PILLAR=[
    '.param controle=1',
    'Vprobe topo 0 1',
    'Rreplica topo sensor {1000*(1+desvio)*(1+erro_sensor)}',
    'Rpadrao sensor 0 1000',
    'Bajuste ajuste 0 V={controle*(1/V(sensor)-2)}',
    'Bcorrecao 0 y I={1u/escala*amortecimento*V(ajuste)*V(y)}',
    '.save V(sensor) V(ajuste) I(Bcorrecao)',
]
PILLAR_SWEEP=[
    '.param caso=0',
    '.param x_inicial=mod(caso,3)-1',
    '.param desvio=(mod(floor(caso/3),3)-1)*0.005',
    '.param passo=if(mod(floor(caso/9),2),2.5u,5u)',
    '.param erro_sensor=(floor(caso/18)-1)*0.0002',
    '.step param caso 0 53 1',
]
(ROOT/'MLC_AND_pilar_validacao.cir').write_text(make_deck(
    '* MLC: pilar de compensacao; 54 execucoes incluindo referencia imperfeita.',PILLAR+PILLAR_SWEEP),encoding='utf-8')
(ROOT/'MLC_AND_pilar_demo.cir').write_text(make_deck(
    '* MLC: comparacao visual com/sem pilar, desvio de +0.5% e erro de +0.02%.',
    PILLAR+['.param desvio=0.005 erro_sensor=0.0002','.step param controle list 0 1']),encoding='utf-8')
