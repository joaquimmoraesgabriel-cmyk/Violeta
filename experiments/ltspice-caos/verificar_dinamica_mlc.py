"""Estimativa independente de Lyapunov das mesmas equacoes normalizadas.

Complementa as medidas LTspice; nao substitui o teste da porta.
Integra estado e vetor tangente por RK4, com renormalizacao regular.
"""
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REVISION2='--v2' in sys.argv
BIAS=-0.005 if REVISION2 else -0.002
AMPLITUDE=0.005 if REVISION2 else 0.002


def derivative(t, state, summed_input):
    x,y,ux,uy=state
    gx=-0.55*x+(-1.02+0.55)/2*(abs(x+1)-abs(x-1))
    slope=-1.02 if abs(x)<1 else -0.55
    return (y-gx,-1.015*y-x+BIAS+summed_input+0.11*math.sin(0.74*t),uy-slope*ux,-ux-1.015*uy)


def rk4(t, state, h, summed_input):
    k1=derivative(t,state,summed_input)
    k2=derivative(t+h/2,tuple(s+h*d/2 for s,d in zip(state,k1)),summed_input)
    k3=derivative(t+h/2,tuple(s+h*d/2 for s,d in zip(state,k2)),summed_input)
    k4=derivative(t+h,tuple(s+h*d for s,d in zip(state,k3)),summed_input)
    return tuple(s+h*(d1+2*d2+2*d3+d4)/6 for s,d1,d2,d3,d4 in zip(state,k1,k2,k3,k4))


def estimate(summed_input,h):
    warmup,block_time,blocks=1000,1000,4
    state=(0.,0.,1.,0.)
    sums=[0.]*blocks
    elapsed=[0.]*blocks
    t=0.
    for index in range(round((warmup+block_time*blocks)/h)):
        state=rk4(t,state,h,summed_input)
        t=(index+1)*h
        if (index+1)%10==0:
            x,y,ux,uy=state
            length=math.hypot(ux,uy)
            if t>warmup:
                block=min(blocks-1,int((t-warmup-1e-8)//block_time))
                sums[block]+=math.log(length)
                elapsed[block]+=10*h
            state=(x,y,ux/length,uy/length)
    return {'soma_entradas':summed_input,'passo_normalizado':h,'expoente_por_bloco':[total/duration for total,duration in zip(sums,elapsed)],'expoente_medio':sum(sums)/sum(elapsed),'duracao_medida_normalizada':sum(elapsed)}


results=[]
for h in (0.02,0.01):
    for summed_input in (-2*AMPLITUDE,0,2*AMPLITUDE):
        result=estimate(summed_input,h)
        results.append(result)
        print(json.dumps(result),flush=True)
(ROOT/('MLC_lyapunov_v2.json' if REVISION2 else 'MLC_lyapunov.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
