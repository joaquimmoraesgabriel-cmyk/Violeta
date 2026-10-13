"""Confirmacao mais lenta / descarga mais rapida; preserva V1 e seus resultados."""
import json
from preparar_etapa18 import ROOT,make
p=ROOT/'MLC_cotas_v1.inc';s=p.read_text(encoding='utf-8')
old='BqTimer 0 timer_cota I={if(V(razao_cota)>0.5,(1-V(timer_cota))/(20u/1n),-V(timer_cota)/(40u/1n))}'
new='BqTimer 0 timer_cota I={if(V(razao_cota)>0.5,(1-V(timer_cota))/(50u/1n),-V(timer_cota)/(20u/1n))}'
assert s.count(old)==1
(ROOT/'MLC_cotas_v2.inc').write_text(s.replace(old,new),encoding='utf-8')
jobs=[make('L2_5_10_v2',politica_l2=1,lat_coord=5e-6,tau_coord=10e-6),
      make('L2_replay_v2',(.625e-6,),politica_l2=1,lat_coord=5e-6,tau_coord=10e-6,falha_super=5),
      make('L2_vies_v2',(.625e-6,),politica_l2=1,lat_coord=5e-6,tau_coord=10e-6,falha_super=4)]
for name in jobs:
    p=ROOT/f'{name}.cir';p.write_text(p.read_text(encoding='utf-8').replace('MLC_cotas_v1.inc','MLC_cotas_v2.inc'),encoding='utf-8')
(ROOT/'lotes_confirmacao_v2.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
(ROOT/'ADENDO_CONFIRMACAO_V2.txt').write_text('''Hipotese de reparo, registrada antes dos oito novos ensaios.

O diagnostico parcial da primeira trajetoria de L2 saudavel mostrou
discrepancias >6.5 uA tambem depois de 30 ms: trechos de cerca de 33.6 us
(5/10 us) e 40.0 us (1/2 us). Portanto estender so a inibicao inicial
nao trata a causa. Nenhum limiar foi ajustado pela nota logica.

V2 preserva limiar/referencia/clock/atuadores/cota de V1. Altera somente
a confirmacao de cotas para carga RC 50 us e descarga 20 us. Uma falha
continua, partindo de zero, cruza 0.7 em -50*ln(0.3)=60.20 us, contra
24.08 us na V1. A memoria parcial impede chamar isso de temporizador
digital de persistencia estrita. O custo e maior latencia; medir no RAW.

Oito trajetorias: L2 5/10 saudavel em dois passos e duas condicoes;
replay e vies extremo em duas condicoes no passo 0.625 us. Nao e uma
nova validacao completa da matriz. Se falhar, preservar o resultado.
Total desta etapa: 64 trajetorias completas, mais SMOKE separado.
''',encoding='utf-8')
print('V2 separada e oito ensaios preparados; total 64.')
