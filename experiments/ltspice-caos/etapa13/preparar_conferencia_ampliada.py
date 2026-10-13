"""Comparacao controlada: quatro atuadores versus soma de A/B/C antes de alocar."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa11'))
from preparar_d import deck

FUSED = '''* A injeta em y; B e C retiram: pedido assinado y=A-B-C.
BdemandaY demanda_y 0 V={V(demanda_a)-V(demanda_b)-V(demanda_c)}
Btotal pedido_total 0 V={abs(V(demanda_y))+abs(V(demanda_d))}
Bglobal ganho_comum 0 V={min(1,orcamento_max/max(V(pedido_total),1p))}
BbaseY base_y 0 V={V(demanda_y)*V(ganho_comum)}
BbaseD base_d 0 V={V(demanda_d)*V(ganho_comum)}
* Mesmas falhas de topo da referencia, abrangendo ambos os atuadores.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bfalha falha_injetada 0 V={janela(time)}
Bmult multiplicador 0 V={if(V(falha_injetada)>0.5,if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(base_y),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreD pre_d 0 V={absdelay(V(base_d),if(falha_coord==2,500u,0))*V(multiplicador)}
Bpretotal sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
BokY ok_y 0 V={if(V(pre_y)*V(demanda_y)<-1e-18,0,V(pre_y))}
BokD ok_d 0 V={if(V(pre_d)*V(demanda_d)<-1e-18,0,V(pre_d))}
Bguard ganho_guard 0 V={min(1,orcamento_max/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
Bguardflag guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(pre_y)*V(demanda_y)<-1e-18,1,if(V(pre_d)*V(demanda_d)<-1e-18,1,0)))}
Breserva reserva_ativa 0 V=0
Bcorrecao_y 0 y I={V(ok_y)*V(ganho_guard)}
Bcorrecao_d 0 x I={V(ok_d)*V(ganho_guard)}
* Sondas de 0 V adicionadas pelo preparador abaixo.
'''

def main():
    ROOT.mkdir(exist_ok=True)
    original = (ROOT.parent / 'etapa12' / 'MLC_coordenadores_falhas.inc').read_text()
    original = original.replace('vntol=1e-9', 'vntol=1e-11')
    start = original.index('* Grupos AB e CD:')
    end = original.index('Bsaida saida')
    fused = original[:start] + FUSED + original[end:]
    # Cada corrente aplicada e medida por uma fonte ideal de 0 V em serie.
    for architecture, model in [('separados', original), ('combinados', fused)]:
        actuators = ['a', 'b', 'c', 'd'] if architecture == 'separados' else ['y', 'd']
        probes = []
        for channel in actuators:
            if channel in ['a', 'y']:
                model = model.replace(f'Bcorrecao_{channel} 0 y I=', f'Bcorrecao_{channel} 0 mede_{channel} I=')
                probes.append(f'Vsense{channel} mede_{channel} y 0')
            elif channel in ['b', 'c']:
                model = model.replace(f'Bcorrecao_{channel} y 0 I=', f'Bcorrecao_{channel} mede_{channel} 0 I=')
                probes.append(f'Vsense{channel} y mede_{channel} 0')
            else:
                model = model.replace('Bcorrecao_d 0 x I=', 'Bcorrecao_d 0 mede_d I=')
                probes.append('Vsensed mede_d x 0')
        # O monitor novo usa as sondas; a soma das amostras RAW e conferida fora do SPICE.
        model = '\n'.join(line for line in model.splitlines() if not line.startswith('Borcamento '))
        model += '\n' + '\n'.join(probes) + '\n'
        model += 'Borcamento orcamento 0 V={' + '+'.join(f'abs(I(Vsense{k}))' for k in actuators) + '}\n'
        if architecture == 'combinados':
            model += 'Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}\n'
            model += 'Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}\n'
        model += 'BpedidoSeparado pedido_separado 0 V={abs(V(demanda_a))+abs(V(demanda_b))+abs(V(demanda_c))+abs(V(demanda_d))}\n'
        model += 'BpedidoLiquido pedido_liquido 0 V={abs(V(demanda_a)-V(demanda_b)-V(demanda_c))+abs(V(demanda_d))}\n'
        model += 'Bcancelamento cancelamento 0 V={max(0,V(pedido_separado)-V(pedido_liquido))}\n'
        (ROOT / f'MLC_{architecture}.inc').write_text(model, encoding='utf-8')

    jobs = []
    source_cases = []
    for profile in range(4):
        source_cases.extend(c for c in json.loads((ROOT.parent / 'etapa12' / f'COORD_perfil{profile}.json').read_text()) if c['politica_coord'] == 0)
    fault_cases = []
    for fault in range(1, 5):
        name = 'COORD_falha4_AB' if fault == 4 else f'COORD_falha{fault}'
        old = json.loads((ROOT.parent / 'etapa12' / f'{name}.json').read_text())
        for step in [2.5e-6, 1.25e-6]:
            fault_cases.extend(dict(c, passo=step) for c in old if c['politica_coord'] == 0)

    for architecture in ['separados', 'combinados']:
        actuators = ['a', 'b', 'c', 'd'] if architecture == 'separados' else ['y', 'd']
        groups = [(f'perfil{p}', [c for c in source_cases if c['perfil'] == p]) for p in range(4)]
        groups += [(f'falha{f}', [c for c in fault_cases if c['falha_coord'] == f]) for f in range(1, 5)]
        for label, cases in groups:
            name = f'SOMA_{architecture}_{label}'
            cases = [dict(c, caso=i) for i, c in enumerate(cases)]
            deck(ROOT, name, f'MLC_{architecture}.inc', cases)
            path = ROOT / f'{name}.cir'
            text = path.read_text()
            saved = '.save V(y) V(referencia) V(ler) V(pedido_separado) V(pedido_liquido) V(cancelamento) '
            saved += ' '.join(f'I(Vsense{k})' for k in actuators)
            text = text.replace('.tran 0', saved + '\n.tran 0', 1)
            measures = '\n'.join(f'.meas tran {metric} {operation} V({node}) FROM 0 TO 0.85' for metric, operation, node in [
                ('cancelamento_medio', 'AVG', 'cancelamento'), ('cancelamento_maximo', 'MAX', 'cancelamento'),
                ('pedido_separado_medio', 'AVG', 'pedido_separado'), ('pedido_liquido_medio', 'AVG', 'pedido_liquido')])
            text = text.replace('.end', measures + '\n.end')
            path.write_text(text, encoding='utf-8')
            jobs.append(name)
    # Intercalar arquiteturas para comparar os mesmos perfis conforme terminam.
    jobs.sort(key=lambda name: (name.rsplit('_', 1)[-1], name))
    (ROOT / 'lotes_ampliados.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    runner = (ROOT.parent / 'etapa12' / 'executar.ps1').read_text()
    (ROOT / 'executar.ps1').write_text(runner, encoding='utf-8')
    print(f'{len(jobs)} decks, 64 trajetorias, 1088 janelas; precisao e capacidade iguais.')

if __name__ == '__main__':
    main()
