"""Reutiliza auditoria fisica da etapa16 e acrescenta evidencia das cotas."""
from pathlib import Path
import csv,hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa16'))
from analisar_etapa16 import analyze,summarize,raw_steps

def extra(name,ts):
    for index,(t,c) in enumerate(raw_steps(ROOT/f'{name}.raw',len(ts))):
        row=ts[index]
        sums=c['v(q_msg_y)'].astype(float)+c['v(q_msg_d)'].astype(float)
        accepted=c['v(quota_y)'].astype(float)+c['v(quota_d)'].astype(float)
        expected=sum(np.abs(c['v(esperado_'+ch+')'].astype(float)) for ch in ['y','d','e'])
        invalid=c['v(quota_invalida)']>.5
        mask=t>=.03
        def mean(v):return float(np.trapezoid(v[mask],t[mask])/(t[-1]-t[mask][0]))
        faultmask=(t>=.343351)&(t<.403349)
        hits=t[invalid & (t>=.34335)]
        yreq=np.abs(c['v(demanda_y)'].astype(float));dreq=np.abs(c['v(demanda_d)'].astype(float))
        row.update(pico_mensagens_uA=float(sums.max()*1e6),pico_cotas_aceitas_uA=float(accepted.max()*1e6),
            pico_concessao_uA=float(expected.max()*1e6),fracao_validador=mean(invalid.astype(float)),
            validador_antes=bool(np.any(invalid & (t>=.002)&(t<.34335))),
            validador_durante=bool(np.any(invalid & faultmask)),
            validador_latencia_us=float((hits[0]-.34335)*1e6) if len(hits) else None,
            cota_inutilizada_uA=mean(np.maximum(0,90e-6-expected))*1e6,
            falta_alocada_y_uA=mean(np.maximum(0,yreq-np.abs(c['v(esperado_y)'])))*1e6,
            falta_alocada_d_uA=mean(np.maximum(0,dreq-np.abs(c['v(esperado_d)']+c['v(esperado_e)'])))*1e6,
            pico_erro_fracao=float(np.abs(c['v(frac_alvo)'].astype(float)-c['v(frac_recebida)']).max()),
            rms_erro_fracao=float(np.sqrt(mean((c['v(frac_alvo)'].astype(float)-c['v(frac_recebida)'])**2))))
        assert row['pico_concessao_uA']<=90.00002, (name,index,row['pico_concessao_uA'])
        assert row['pico_cotas_aceitas_uA']<=90.00002

def main():
    specs=[(ROOT.parent/'etapa15',f'BUF_p3_f{f}') for f in [0,4,2,3]]
    specs += [(ROOT.parent/'etapa16','E_cota5_f0'),(ROOT.parent/'etapa16','R_base')]
    for p in sorted(ROOT.glob('lotes_*.json')):
        specs += [(ROOT,n) for n in json.loads(p.read_text(encoding='utf-8'))]
    specs=list(dict.fromkeys(specs));ts=[];rows=[];pending=[]
    cache=ROOT/'cache_analise';cache.mkdir(exist_ok=True)
    codehash=hashlib.sha256(Path(__file__).read_bytes()+(ROOT.parent/'etapa16/analisar_etapa16.py').read_bytes()).hexdigest()
    for folder,name in specs:
        try:
            sig=[codehash]+[(folder/f'{name}{s}').stat().st_mtime_ns for s in ['.cir','.json','.log','.raw']]
            target=cache/f'{folder.name}_{name}.json'
            data=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
            if data.get('signature')==sig:a,b=data['trajectories'],data['rows']
            else:
                a,b=analyze(folder,name)
                if folder==ROOT:extra(name,a)
                target.write_text(json.dumps(dict(signature=sig,trajectories=a,rows=b)),encoding='utf-8')
        except (FileNotFoundError,ValueError) as err:
            if '--partial' not in sys.argv:raise
            pending.append(f'{name}: {err}');continue
        ts+=a;rows+=b
    suffix='_parcial' if '--partial' in sys.argv else ''
    for name,data in [('trajetorias',ts),('resumo',summarize(ts,rows)),('pendentes',pending)]:
        (ROOT/f'{name}{suffix}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    if rows:
        with (ROOT/f'janelas{suffix}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for s in summarize(ts,rows):
        print(f"{s['arquivo']}: {s['corretas']}/{s['janelas']}, pares={s['pares']}, RD={s['rms_residuo_d_uA']:.3f}, RY={s['rms_residuo_y_uA']:.3f}, alarmes={s['alarmes_indevidos']}, pico={s['pico_corrente_uA']:.5f}")
    print(f'Novas={sum(t["origem"]=="etapa17" for t in ts)}, pendentes={len(pending)}')

if __name__=='__main__':main()
