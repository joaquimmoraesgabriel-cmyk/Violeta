"""Auditoria fisica herdada, mais deteccao e recuperacao das cotas."""
from pathlib import Path
import csv, hashlib, json, sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa16'))
from analisar_etapa16 import analyze, summarize, raw_steps

def extra(name,ts):
    for index,(t,c) in enumerate(raw_steps(ROOT/f'{name}.raw',len(ts),max_last_gaps=[r['passo'] for r in ts])):
        row=ts[index];fault=row['falha_super'];start=0 if fault in [0,2,5] else .34335
        end=.85 if fault in [0,2,5] else .40335
        m=t>=.03;active=t>=.002;before=active & (t<start if fault else True)
        def mean(v):return float(np.trapezoid(np.asarray(v,dtype=float)[m],t[m])/(t[-1]-t[m][0]))
        trip=c['v(trip_cota)']>.5;reserve=c['v(reserva_cota)']>.5
        during=(t>=start)&(t<=end)
        early=bool(np.any(trip & before))
        detected=bool(np.any(trip & during) and not early) if fault else None
        def first(mask):
            times=t[mask & (t>=start)]
            return float((times[0]-start)*1e6) if len(times) else None
        expected=sum(np.abs(c[f'v(esperado_{ch})'].astype(float)) for ch in ['y','d','e'])
        accepted=c['v(quota_y)'].astype(float)+c['v(quota_d)'].astype(float)
        messages=c['v(q_msg_y)'].astype(float)+c['v(q_msg_d)'].astype(float)
        physical=sum(np.abs((c[f'v(x{ch}:entrada_shunt)'].astype(float)-c[f'v(br_{ch})'].astype(float))/1000) for ch in ['y','d','e'])
        row.update(
            cota_alarme_indevido=early,
            cota_reserva_indevida=bool(np.any(reserve & before)),
            cota_alarme_durante=bool(np.any(trip & during)) if fault else None,
            cota_alarme_detectado=detected,
            cota_alarme_somente_apos_falha=bool(np.any(trip & (t>end)) and not early and not detected) if fault else None,
            cota_latencia_alarme_us=first(trip & during) if detected else None,
            cota_latencia_reserva_us=first(reserve & during) if detected else None,
            cota_primeiro_alarme_ms=float(t[trip][0]*1e3) if np.any(trip) else None,
            cota_reserva_retida=bool(reserve[-1]),
            cota_fracao_reserva=mean(reserve),
            cota_fracao_incoerente=mean(c['v(incoerente)']>.5),
            cota_fracao_idade_invalida=mean(c['v(idade_invalida)']>.5),
            cota_fracao_guarda_basica=mean(c['v(quota_invalida)']>.5),
            cota_primeira_idade_invalida_us=first((c['v(idade_invalida)']>.5)&active),
            cota_primeira_incoerencia_us=first((c['v(incoerente)']>.5)&active),
            cota_pico_erro_uA=float(c['v(erro_cota)'][active].max()*1e6),
            cota_pico_timer_sadio=float(c['v(timer_cota)'][before].max()) if np.any(before) else None,
            cota_idade_min_us=float(c['v(idade_cota)'][active].min()*1e6),
            cota_idade_max_us=float(c['v(idade_cota)'][active].max()*1e6),
            pico_mensagens_uA=float(messages.max()*1e6),
            pico_cotas_aceitas_uA=float(accepted.max()*1e6),
            pico_concessao_uA=float(expected.max()*1e6),
            cota_inutilizada_uA=mean(np.maximum(0,90e-6-expected))*1e6,
            corrente_fracao_acima_90_005=mean(physical>90.005e-6),
            cota_limite_falha=bool(accepted.max()>90.00002e-6 or expected.max()>90.00002e-6))
        # Fallback deve cumprir a definicao local, avaliada so depois da transicao.
        y=np.abs(c['v(demanda_y)'].astype(float));d=np.abs(c['v(demanda_d)'].astype(float))
        target=90e-6*y/np.maximum(y+d,1e-12)
        row['cota_erro_reserva_local_uA']=float(np.max(np.abs(c['v(quota_y)'][reserve]-target[reserve]))*1e6) if np.any(reserve) else None

def main():
    cache=ROOT/'cache_analise';cache.mkdir(exist_ok=True)
    codehash=hashlib.sha256(Path(__file__).read_bytes()+(ROOT.parent/'etapa16/analisar_etapa16.py').read_bytes()+(ROOT.parent/'etapa12/leitura_independente.py').read_bytes()).hexdigest()
    names=list(dict.fromkeys(n for p in sorted(ROOT.glob('lotes_*.json')) for n in json.loads(p.read_text(encoding='utf-8'))))
    ts=[];rows=[];pending=[]
    for name in names:
        try:
            sig=[codehash]+[(ROOT/f'{name}{ext}').stat().st_mtime_ns for ext in ['.cir','.json','.log','.raw']]
            path=cache/f'{name}.json';data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            if data.get('signature')==sig:a,b=data['trajectories'],data['rows']
            else:
                a,b=analyze(ROOT,name);extra(name,a)
                path.write_text(json.dumps(dict(signature=sig,trajectories=a,rows=b)),encoding='utf-8')
        except (FileNotFoundError,ValueError) as e:
            if '--partial' not in sys.argv:raise
            pending.append(f'{name}: {e}');continue
        ts+=a;rows+=b
    suffix='_parcial' if '--partial' in sys.argv else ''
    for name,data in [('trajetorias',ts),('resumo',summarize(ts,rows)),('pendentes',pending)]:
        (ROOT/f'{name}{suffix}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    if rows:
        with (ROOT/f'janelas{suffix}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for s in summarize(ts,rows):
        part=[r for r in ts if r['arquivo']==s['arquivo']]
        print(f"{s['arquivo']}: {s['corretas']}/{s['janelas']}, pares={s['pares']}, falsos_cota={sum(r['cota_alarme_indevido'] for r in part)}, deteccoes={sum(bool(r['cota_alarme_detectado']) for r in part)}, pico={s['pico_corrente_uA']:.5f}")
    print(f'Trajetorias={len(ts)}, pendentes={len(pending)}')

if __name__=='__main__':main()
