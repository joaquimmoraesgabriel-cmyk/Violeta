"""Supervisor causal amostrado e decks LTspice; nenhuma verdade logica no seletor."""
from pathlib import Path
import json,random,math
import numpy as np
ROOT=Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
SEQ=[0,0,1,0,2,0,3,1,1,2,1,3,2,2,3,3,0]
DT=.0001; WAKE=.0002; PERIOD=.005; AUDIT=.0006; THRESH=.001
POLICIES=['nove_fixos','tres_fixos','rodizio','sorteio','adaptativo']
PROFILES=['saudaveis','uma_falha','quatro_falhas','erro_comum','ruido_alto']
def source(name,node,shift):
    pairs=[(0,(SEQ[0]>>shift)&1)]
    for i in range(1,17):pairs.extend([(i*.05,(SEQ[i-1]>>shift)&1),(i*.05+1e-6,(SEQ[i]>>shift)&1)])
    pairs.append((.85,(SEQ[-1]>>shift)&1))
    return f'{name} {node} 0 PWL('+' '.join(f'{t:.6f} {v}' for t,v in pairs)+')'
def events(profile):
    groups={1:([0],[7]),2:([0,1,2,3],[2,5,7,8]),3:(list(range(9)),list(range(9)))}
    if profile not in groups:return []
    a,b=groups[profile]
    return [{'inicio':.16335,'fim':.36335,'sensores':a,'offset':.02},{'inicio':.46335,'fim':.68335,'sensores':b,'offset':-.02}]
def readings(t,profile):
    true=.010*math.sin(2*math.pi*137*t+math.radians(40))
    values=np.array([true-.0002+(i-4)*.00002+(.0007 if profile==4 else .00005)*math.sin(2*math.pi*(311+47*i)*t+.53*i) for i in range(9)])
    for e in events(profile):
        if e['inicio']<=t<e['fim']:
            values[e['sensores']]+=e['offset']
    return values
def schedule(profile,policy,seed):
    rng=random.Random(seed)
    last_group=-1; on=np.zeros(9,dtype=bool);since=np.zeros(9)
    selected=np.array([0,1,2]); audit_until=AUDIT; next_audit=PERIOD
    last_est=0.; alarm_since=None; alarms=[]; estimates=[]; commands=[]; ready_counts=[]; masks=[]; exchanges=0
    for tick in range(round(.85/DT)+1):
        t=tick*DT
        vals=readings(t,profile)
        if policy=='nove_fixos':wanted=np.ones(9,dtype=bool)
        elif policy=='tres_fixos':wanted=np.array([i<3 for i in range(9)])
        elif policy in ['rodizio','sorteio']:
            group=int((t+1e-10)/PERIOD)
            if group!=last_group:
                selected=np.arange((group%3)*3,(group%3)*3+3) if policy=='rodizio' else np.array(sorted(rng.sample(range(9),3)))
                last_group=group
            wanted=np.array([i in selected for i in range(9)])
        else:
            if t+1e-10>=next_audit:
                audit_until=max(audit_until,t+AUDIT);next_audit+=PERIOD
            # A decisao deste tick usa apenas leituras validas do tick anterior.
            wanted=np.ones(9,dtype=bool) if t<audit_until-1e-10 else np.array([i in selected for i in range(9)])
        exchanges+=int(np.count_nonzero(wanted!=on))
        since[wanted & ~on]=t;on=wanted
        valid=on & ((t-since)>=WAKE-1e-10)
        idx=np.flatnonzero(valid)
        spread=float(np.ptp(vals[idx])) if len(idx)>1 else 0.
        alarm=spread>THRESH
        alarms.append(alarm)
        if len(idx):last_est=float(np.median(vals[idx]))
        if policy=='adaptativo':
            if alarm:
                if alarm_since is None:alarm_since=t
                if t-alarm_since>=DT-1e-10 and len(idx)<9:
                    audit_until=max(audit_until,t+.002)
            else:alarm_since=None
            if len(idx)==9:
                # Candidatos concordantes com a mediana; nao usar identidade de falhas.
                residual=np.abs(vals-last_est)
                good=np.flatnonzero(residual<=THRESH*.5)
                if len(good)>=3:
                    selected=np.array(sorted(sorted(good,key=lambda i:(residual[i],i))[:3]))
        estimates.append(last_est);commands.append(int(on.sum()));ready_counts.append(int(valid.sum()));masks.append(int(sum(1<<int(i) for i in np.flatnonzero(on))))
    detections=[]
    for e in events(profile):
        a=math.ceil(e['inicio']/DT);b=math.ceil(e['fim']/DT)
        hits=[k for k in range(a,b) if alarms[k]]
        detections.append({'inicio':e['inicio'],'fim':e['fim'],'sensores':e['sensores'],'primeiro_alarme_s':hits[0]*DT if hits else None,'latencia_ms':(hits[0]*DT-e['inicio'])*1000 if hits else None})
    healthy_ticks=[k for k in range(len(alarms)) if not any(e['inicio']<=k*DT<e['fim'] for e in events(profile))]
    stats={'perfil':PROFILES[profile],'politica':policy,'semente':seed,'dt_us':DT*1e6,'despertar_us':WAKE*1e6,'periodo_us':PERIOD*1e6,'media_ligados':float(np.mean(commands)),'max_ligados':max(commands),'media_validos':float(np.mean(ready_counts)),'tempo_sem_leitura_valida_ms':float(np.count_nonzero(np.array(ready_counts)==0)*DT*1000),'trocas_individuais':exchanges,'fracao_alarme_sem_falha':sum(alarms[k] for k in healthy_ticks)/len(healthy_ticks),'deteccoes':detections}
    return estimates,commands,ready_counts,masks,stats
def pwl(name,node,values):
    # Hold causal: valor k vale ate a proxima amostra; degrau com borda 1 ns.
    pairs=[(0,values[0])]
    for k in range(1,len(values)):
        t=k*DT;pairs.extend([(t-1e-9,values[k-1]),(t,values[k])])
    return f'{name} {node} 0 PWL('+' '.join(f'{t:.9f} {v:.10g}' for t,v in pairs)+')\n'
base=(ROOT.parent/'etapa8'/'MLC_limites.inc').read_text()
base=base.replace('BsensorB estimativa_b 0 V={V(pert_b)+erro_b}','* estimativa_b vem do supervisor amostrado externo e causal.')
(ROOT/'MLC_seletivo.inc').write_text(base,encoding='utf-8')
configs=[]
for profile in range(5):
    for policy in POLICIES:
        for seed in ([19,73,211] if policy=='sorteio' else [19]):
            name=f'SEL_p{profile}_{policy}_s{seed}'
            est,on,valid,mask,stats=schedule(profile,policy,seed)
            (ROOT/(name+'_sinais.inc')).write_text(pwl('Vestimativa','estimativa_b',est)+pwl('Vativos','ativos',on)+pwl('Vvalidos','validos',valid)+pwl('Vmascara','mascara',mask),encoding='utf-8')
            (ROOT/(name+'_supervisor.json')).write_text(json.dumps(stats,indent=2),encoding='utf-8')
            lines=['* Selecao causal; replicas favoraveis, despertar e ruido definidos.','.include MLC_seletivo.inc',f'.include {name}_sinais.inc',source('Va','entrada_a',1),source('Vb','entrada_b',0),'.param perfil=1 politica=2 atraso_coord=0 orcamento_max=100u','.param x_inicial=if(inicial,0.37,-0.37) y_inicial=-0.2 passo=5u','.step param inicial list 0 1','.save V(x) V(saida) V(referencia) V(ler) V(ativos) V(validos) V(estimativa_b) V(orcamento)','.tran 0 0.85 0 {passo} uic']
            for i in range(17):
                for label,op,trace in [('minimo','MIN','V(x)'),('maximo','MAX','V(x)')]:lines.append(f'.meas tran {label}_{i:02} {op} {trace} FROM {i*.05+.03:.6f} TO {(i+1)*.05-.001:.6f}')
            lines+=['.meas tran pico_orcamento MAX V(orcamento) FROM 0 TO 0.85','.end','']
            (ROOT/(name+'.cir')).write_text('\n'.join(lines),encoding='utf-8')
            configs.append({'nome':name,'perfil':PROFILES[profile],'politica_selecao':policy,'semente':seed,'passo_us':5,'estados_iniciais':[-.37,.37]})
(ROOT/'casos_selecao.json').write_text(json.dumps(configs,indent=2),encoding='utf-8')
print(f'{len(configs)} decks, {len(configs)*2} trajetorias; cinco perfis, cinco politicas, tres sementes do sorteio.')
