"""Integra candidato aprovado na bancada, mantendo ablacões ideais separadas."""
from pathlib import Path
import json
from preparar_etapa14 import CONTROL, write

ROOT = Path(__file__).resolve().parent

def main():
    model = (ROOT / 'atuadores_antiwindup.inc').read_text()
    model = model.replace(' gbw_drive=2Meg', '').replace(' vos_drive=0', '')
    model = model.replace('params: erro_r=0', 'params: erro_r=0 voff=0 gbw=2Meg')
    model = model.replace('GBW={gbw_drive}', 'GBW={gbw}').replace('Vos={vos_drive}', 'Vos={voff}')
    (ROOT / 'atuadores_etapa14.inc').write_text(model, encoding='utf-8')
    core = (ROOT / 'MLC_detector_reserva.inc').read_text()
    start = core.index('* Atuacao ideal da ablacao;')
    end = core.index('* Grandezas do detector escaladas:')
    physical = '''* Circuito de atuacao: modelo ADI, shunt, isolador, RC e realimentacao.
.include atuadores_etapa14.inc
.param margem_limite=90u gbw_limit=100Meg tau_cmd=2u
Vp vp 0 5
Vm vm 0 -5
Rstart vp partida 100k
Cstart partida 0 100p IC=0
Bready habilitado 0 V={if(V(partida)>3,if(V(vp)>4,1,0),0)}
BnormY norm_y 0 V={escala_med*V(comando_y)}
BnormD norm_d 0 V={escala_med*V(comando_d)}
RcmdY norm_y filtro_y 1000
CcmdY filtro_y 0 {tau_cmd/1000} IC=0
RcmdD norm_d filtro_d 1000
CcmdD filtro_d 0 {tau_cmd/1000} IC=0
BphyY phy_y 0 V={V(filtro_y)/escala_med*V(ganho_fisico)}
BphyD phy_d 0 V={V(filtro_d)/escala_med*V(ganho_fisico)}
XY phy_y br_y vp vm med_y habilitado ATUADOR
XD phy_d br_d vp vm med_d habilitado ATUADOR
XL med_y med_d vp vm ganho_fisico LIMITADOR
Vsensey br_y y 0
Vsensed br_d x 0
'''
    core = core[:start] + physical + core[end:]
    # O detector compara com a mesma resposta RC conhecida do comando.
    for channel in ['Y', 'D']:
        lower = channel.lower()
        old = f'Bexp{channel} exp_{lower} 0 V={{escala_med*V(esperado_{lower})}}'
        new = f'Bexp{channel} exp_{lower}_cmd 0 V={{escala_med*V(esperado_{lower})}}\nRexpCmd{channel} exp_{lower}_cmd exp_{lower} 1000\nCexpCmd{channel} exp_{lower} 0 {{tau_cmd/1000}} IC=0'
        core = core.replace(old, new)
    (ROOT / 'MLC_circuito_reserva.inc').write_text(core, encoding='utf-8')
    originals = json.loads((ROOT.parent / 'etapa13' / 'SOMA_combinados_perfil1.json').read_text())
    jobs = []
    for detector in [0, 1]:
        for fault in [0, 4]:
            cases = [dict(c, caso=i, detector=detector, falha_coord=fault, cap_operacao=90e-6, hardware=1)
                     for i, c in enumerate(c for c in originals if c['passo'] == 1.25e-6)]
            name = f'PHY_d{detector}_falha{fault}'
            write(name, cases, 'MLC_circuito_reserva.inc')
            path = ROOT / f'{name}.cir'
            text = path.read_text().replace('.tran 0', '.save V(ganho_fisico) V(habilitado) I(Vp) I(Vm)\n.tran 0', 1)
            path.write_text(text, encoding='utf-8')
            jobs.append(name)
    (ROOT / 'lotes_circuito.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    print('Oito trajetorias com circuito de atuacao, reserva ligada/desligada e falha silenciosa.')

if __name__ == '__main__':
    main()
