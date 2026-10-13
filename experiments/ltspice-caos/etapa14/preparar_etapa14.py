"""Detector causal, reserva independente e ensaios pareados de falha do topo."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'etapa11'))
from preparar_d import deck

CONTROL = '''* Dois pedidos assinados. O calculo local de reserva continua ativo.
.param r_med=1000 escala_med=10000 tau_med=4u tau_confirmacao=10u erro_med=0.5u ruido_med=0.5u
BdemandaY demanda_y 0 V={V(demanda_a)-V(demanda_b)-V(demanda_c)}
Bpedido pedido_total 0 V={abs(V(demanda_y))+abs(V(demanda_d))}
Blocal ganho_local 0 V={min(1,cap_operacao/max(V(pedido_total),1p))}
BesperadoY esperado_y 0 V={V(demanda_y)*V(ganho_local)}
BesperadoD esperado_d 0 V={V(demanda_d)*V(ganho_local)}
* Somente este bloco injeta falha. O detector nao recebe falha_coord nem janela.
.func janela(t) {if(t>=0.34335,if(t<0.40335,1,0),0)}
Bmult multiplicador 0 V={if(janela(time),if(falha_coord==1,0,if(falha_coord==3,-1,if(falha_coord==4,0,1))),1)}
BpreY pre_y 0 V={absdelay(V(esperado_y),if(falha_coord==2,500u,0))*V(multiplicador)}
BpreD pre_d 0 V={absdelay(V(esperado_d),if(falha_coord==2,500u,0))*V(multiplicador)}
Bheartbeat heartbeat 0 V={if(falha_coord==1,1-janela(time),1)}
Bpretotal sem_protecao 0 V={abs(V(pre_y))+abs(V(pre_d))}
* A reserva usa seus calculos atuais; nao os comandos defeituosos do topo.
BselY selecionado_y 0 V={if(V(reserva_ativa)>0.5,V(esperado_y),V(pre_y))}
BselD selecionado_d 0 V={if(V(reserva_ativa)>0.5,V(esperado_d),V(pre_d))}
BokY ok_y 0 V={if(V(selecionado_y)*V(demanda_y)<-1e-18,0,V(selecionado_y))}
BokD ok_d 0 V={if(V(selecionado_d)*V(demanda_d)<-1e-18,0,V(selecionado_d))}
Bguard ganho_guard 0 V={min(1,cap_operacao/max(abs(V(ok_y))+abs(V(ok_d)),1p))}
BguardF guard_ativo 0 V={if(V(ganho_guard)<0.999999,1,if(V(selecionado_y)*V(demanda_y)<-1e-18,1,if(V(selecionado_d)*V(demanda_d)<-1e-18,1,0)))}
BcmdY comando_y 0 V={V(ok_y)*V(ganho_guard)}
BcmdD comando_d 0 V={V(ok_d)*V(ganho_guard)}
* Atuacao ideal da ablacao; shunts reais, sondas de 0 V para verificacao externa.
Bcorrecao_y 0 n_y I={V(comando_y)}
Bcorrecao_d 0 n_d I={V(comando_d)}
RmedY n_y br_y {r_med}
RmedD n_d br_d {r_med}
Vsensey br_y y 0
Vsensed br_d x 0
BmedY med_y 0 V={V(n_y,br_y)/r_med}
BmedD med_d 0 V={V(n_d,br_d)/r_med}
* Grandezas do detector escaladas: 100 uA corresponde a 1 V.
BobsY obs_y 0 V={escala_med*(V(med_y)+erro_med+ruido_med*sin(2*pi*13007*time))}
BobsD obs_d 0 V={escala_med*(V(med_d)-erro_med+ruido_med*sin(2*pi*17011*time+0.7))}
BexpY exp_y 0 V={escala_med*V(esperado_y)}
BexpD exp_d 0 V={escala_med*V(esperado_d)}
RobsY obs_y obs_y_f 1000
CobsY obs_y_f 0 {tau_med/1000} IC=0
RobsD obs_d obs_d_f 1000
CobsD obs_d_f 0 {tau_med/1000} IC=0
RexpY exp_y exp_y_f 1000
CexpY exp_y_f 0 {tau_med/1000} IC=0
RexpD exp_d exp_d_f 1000
CexpD exp_d_f 0 {tau_med/1000} IC=0
Berro discrepancia 0 V={abs(V(obs_y_f)-V(exp_y_f))+abs(V(obs_d_f)-V(exp_d_f))}
Blimiar limiar 0 V={escala_med*3u+0.1*(abs(V(exp_y_f))+abs(V(exp_d_f)))}
Bdiv divergente 0 V={if(time>2m,if(abs(V(exp_y_f))+abs(V(exp_d_f))>escala_med*5u,if(V(discrepancia)>V(limiar),1,0),0),0)}
* Confirmacao RC, seguida de memoria. Reset requer intervencao futura.
Ctimer timer 0 1n IC=0
Btimer 0 timer I={if(V(divergente)>0.5,(1-V(timer))/(tau_confirmacao/1n),-V(timer)/(2*tau_confirmacao/1n))}
Btrip trip 0 V={if(V(timer)>0.7,1,0)}
Cmem memoria 0 1n IC=0
Bmem 0 memoria I={max(V(trip)-V(memoria),0)/1000}
Rmem memoria 0 1T
Breserva reserva_ativa 0 V={if(detector,if(V(memoria)>0.5,1,0),0)}
Borcamento orcamento 0 V={abs(V(med_y))+abs(V(med_d))}
Bfalta falta 0 V={max(0,V(pedido_total)-V(orcamento))}
Bsobra sobra 0 V={min(max(0,orcamento_max-V(orcamento)),V(falta))}
'''

def build():
    original = (ROOT.parent / 'etapa13' / 'MLC_combinados.inc').read_text()
    start = original.index('* A injeta em y;')
    end = original.index('Bsaida saida')
    tail = '\n'.join(line for line in original[end:].splitlines()
                     if not line.startswith(('Vsense', 'Borcamento', 'Bfalta', 'Bsobra', 'BpedidoSeparado', 'BpedidoLiquido', 'Bcancelamento')))
    model = original[:start] + CONTROL + tail + '\n'
    (ROOT / 'MLC_detector_reserva.inc').write_text(model, encoding='utf-8')
    jobs = []
    originals = json.loads((ROOT.parent / 'etapa13' / 'SOMA_combinados_perfil1.json').read_text())
    for detector in [0, 1]:
        for fault in [0, 1, 2, 3, 4]:
            cases = [dict(c, caso=i, detector=detector, falha_coord=fault, cap_operacao=100e-6, hardware=0)
                     for i, c in enumerate(originals)]
            name = f'DET_d{detector}_falha{fault}'
            write(name, cases)
            jobs.append(name)
    # Referencia com margem para isolar custo de corrente de futuro hardware.
    for fault in [0, 4]:
        cases = [dict(c, caso=i, detector=1, falha_coord=fault, cap_operacao=90e-6, hardware=0)
                 for i, c in enumerate(c for c in originals if c['passo'] == 1.25e-6)]
        name = f'DET_margem_falha{fault}'
        write(name, cases)
        jobs.append(name)
    jobs.sort(key=lambda name: (name.rsplit('_', 1)[-1], name))
    (ROOT / 'lotes_detector.json').write_text(json.dumps(jobs, indent=2), encoding='utf-8')
    (ROOT / 'executar.ps1').write_text((ROOT.parent / 'etapa13' / 'executar.ps1').read_text(), encoding='utf-8')
    print('Detector: 44 trajetorias, 748 janelas; referencia e reserva sob os mesmos comandos e limite.')

def write(name, cases, model='MLC_detector_reserva.inc'):
    deck(ROOT, name, model, cases)
    path = ROOT / f'{name}.cir'
    text = path.read_text()
    saved = '.save V(y) V(referencia) V(ler) V(reserva_ativa) V(timer) V(trip) V(divergente) V(discrepancia) V(limiar) V(heartbeat) V(esperado_y) V(esperado_d) V(med_y) V(med_d) V(comando_y) V(comando_d) I(Vsensey) I(Vsensed)'
    text = text.replace('.tran 0', saved + '\n.tran 0', 1)
    text = text.replace('.end', '.meas tran pico_discrepancia MAX V(discrepancia) FROM 0 TO 0.85\n.end')
    path.write_text(text, encoding='utf-8')

if __name__ == '__main__':
    build()
