"""Recalcula somente quatro fracoes temporais dos arquivos anteriores.

Nao simula novamente e nao altera RAWs, parametros, janelas, RMS ou picos.
Executar depois dos lotes pesados para evitar competicao de memoria/IO.
"""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'etapa12'))
from leitura_independente import raw_steps
archive=ROOT/'backup_fracoes_anteriores';archive.mkdir(exist_ok=True)
datasets={stage:json.loads((ROOT.parent/stage/'trajetorias.json').read_text(encoding='utf-8')) for stage in ['etapa16','etapa17']}
keys=['fracao_fora_quebras','fracao_e','fracao_limitador','fracao_demanda_real_acima_90']
specs=sorted({(t['origem'],t['arquivo']) for rows in datasets.values() for t in rows})
corrections={};sources=[]
for origin,name in specs:
    folder=ROOT.parent/origin
    assert folder.resolve().parent==ROOT.parent.resolve()
    cases=json.loads((folder/f'{name}.json').read_text(encoding='utf-8'))
    for index,(t,c) in enumerate(raw_steps(folder/f'{name}.raw',len(cases),max_last_gaps=[p['passo'] for p in cases])):
        p=cases[index];m=t>=.03;tt=t[m]
        def mean(v):return float(np.trapezoid(np.asarray(v,dtype=float)[m],tt)/(tt[-1]-tt[0]))
        x=c['v(x)'].astype(float);y=c['v(y)'].astype(float)
        g=-.55*x+(-1.02+.55)/2*(np.abs(x+1)-np.abs(x-1))
        pa=p['amp_a']*np.sin(2*np.pi*500*t)
        pb=p['amp_b']*np.sin(2*np.pi*137*t+np.deg2rad(40))
        pc=p['amp_c']*np.sin(2*np.pi*73*t+np.deg2rad(65))
        pd=p['amp_d']*np.sin(2*np.pi*211*t+np.deg2rad(17))
        desired_d=.01*pd*g
        desired_y=.01*(1.015*pa*y-pb-pc*np.sin(.74*t/100e-6))
        e=(c['v(xe:entrada_shunt)'].astype(float)-c['v(br_e)'].astype(float))/1000 if 'v(xe:entrada_shunt)' in c else np.zeros(len(t))
        values=dict(fracao_fora_quebras=mean(np.abs(x)>1),fracao_e=mean(np.abs(e)>1e-6),
                    fracao_limitador=mean(c['v(ganho_fisico)']<.999),
                    fracao_demanda_real_acima_90=mean(np.abs(desired_d)+np.abs(desired_y)>91e-6))
        assert all(0<=v<=1 for v in values.values())
        corrections[origin,name,index]=values
    p=folder/f'{name}.raw';sources.append(dict(origem=origin,arquivo=name,raw_bytes=p.stat().st_size,raw_mtime_ns=p.stat().st_mtime_ns))
    print(f'Recalculado {origin}/{name}',flush=True)

changes=[]
for stage,rows in datasets.items():
    unchanged_before=json.dumps([{k:v for k,v in row.items() if k not in keys} for row in rows],sort_keys=True)
    for row in rows:
        values=corrections[row['origem'],row['arquivo'],row['caso']]
        old={k:row[k] for k in keys}
        assert all(values[k]+1e-10>=old[k] for k in keys),(stage,row['arquivo'],row['caso'])
        row.update(values)
        changes.append(dict(arquivo=stage+'/trajetorias.json',ensaio=row['arquivo'],caso=row['caso'],antes=old,depois=values))
    assert unchanged_before==json.dumps([{k:v for k,v in row.items() if k not in keys} for row in rows],sort_keys=True)
    folder=ROOT.parent/stage
    for filename in ['trajetorias.json','resumo.json','ETAPA'+stage[5:]+'_RESULTADOS.txt']:
        source=folder/filename;backup=archive/(stage+'_'+filename)
        if not backup.exists():backup.write_bytes(source.read_bytes())
    (folder/'trajetorias.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    path=folder/'resumo.json';summary=json.loads(path.read_text(encoding='utf-8'))
    for group in summary:
        ts=[r for r in rows if r['arquivo']==group['arquivo']]
        for k in ['fracao_fora_quebras','fracao_e']:group[k]=float(np.mean([r[k] for r in ts]))
    path.write_text(json.dumps(summary,indent=2),encoding='utf-8')

# A unica tabela de fracoes impressa nesses dois relatorios e a demanda >91 uA na Etapa16.
path=ROOT.parent/'etapa16/ETAPA16_RESULTADOS.txt';text=path.read_text(encoding='utf-8')
lines=text.splitlines();corrected_table=[]
start=next(i for i,line in enumerate(lines) if line.startswith('Condição saudável | Demanda exata >91'))
for i in range(start+2,start+7):
    cols=lines[i].split('|');name=cols[0].strip();ts=[r for r in datasets['etapa16'] if r['arquivo']==name]
    assert len(ts)==4,name
    value=100*float(np.mean([r['fracao_demanda_real_acima_90'] for r in ts]))
    cols[1]=f' {value:.2f}'.ljust(len(cols[1]));lines[i]='|'.join(cols)
    corrected_table.append(dict(arquivo=name,demanda_acima_91_percentual=value))
text='\n'.join(lines)+'\n'
note='CORRECAO METODOLOGICA DA ETAPA18: fracoes temporais recalculadas dos RAWs com indicadores convertidos a float. Janelas, RMS, picos e parametros preservados. Evidencia em ../etapa18/correcao_fracoes_anteriores.json.'
if note not in text:text+='\n'+note+'\n'
path.write_text(text,encoding='utf-8')
path=ROOT.parent/'etapa17/ETAPA17_RESULTADOS.txt';text=path.read_text(encoding='utf-8')
if note not in text:path.write_text(text.rstrip()+'\n\n'+note+'\n',encoding='utf-8')
out=dict(trajetorias_unicas=len(corrections),registros_atualizados=len(changes),arquivos_raw=len(specs),
    campos=keys,tabela_corrigida=corrected_table,alteracoes=changes,fontes=sources,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    nota='Backups anteriores preservados. Caches antigos invalidos pelo hash do helper; proxima analise os regenera.')
(ROOT/'correcao_fracoes_anteriores.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(trajetorias_unicas=len(corrections),registros_atualizados=len(changes),tabela_corrigida=corrected_table)))
