"""Compara somente trajetorias saudaveis pareadas em alta demanda."""
from pathlib import Path
import csv
import json
from analisar_etapa15 import analyze

ROOT=Path(__file__).resolve().parent

def main():
    ts,rows=[],[]
    for name in json.loads((ROOT/'lotes_ablacao.json').read_text()):
        a,b=analyze(name);ts.extend(a);rows.extend(b)
    assert len(ts)==8
    (ROOT/'ablacao_trajetorias.json').write_text(json.dumps(ts,indent=2),encoding='utf-8')
    with (ROOT/'ablacao_janelas.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    main_ts,_=analyze('EXP_p3_f0_d1')
    groups=[('Circuito não ideal, 90 µA',main_ts)]
    groups += [(f'Atuador ideal com RC, {cap} µA',[t for t in ts if abs(t['cap_operacao']-cap*1e-6)<1e-12]) for cap in [90,100]]
    lines=['# Controle de capacidade e dinâmica — alta demanda saudável','',
           'O filtro de comando de 2 µs, a partida, a lógica e o detector são mantidos. O atuador ideal substitui o amplificador e o limitador realimentado por uma fonte de corrente; sua capacidade é imposta pela guarda de comando. Este controle não valida um limitador físico.', '',
           '| Realização | Acertos 1,25 µs | Acertos 0,625 µs | Corretas nos dois passos | Classificações diferentes | Pico shunts (µA) |',
           '|---|---:|---:|---:|---:|---:|']
    summaries=[]
    for label,subset in groups:
        bystep={s:{(t['x_inicial'],j):int(j not in t['janelas_falhas']) for t in subset if t['passo']==s for j in range(17)} for s in [1.25e-6,.625e-6]}
        a,b=bystep.values()
        assert a.keys()==b.keys() and len(a)==34
        summary=dict(realizacao=label,corretas_125=sum(a.values()),corretas_0625=sum(b.values()),
                     corretas_ambos=sum(a[k] and b[k] for k in a), divergencias=sum(a[k]!=b[k] for k in a),
                     pico_tensoes_uA=max(t['pico_tensoes_uA'] for t in subset),
                     alarmes_indevidos=sum(t['alarme_indevido'] for t in subset),
                     falhas_corrente=sum(t['corrente_falha_tensoes'] for t in subset))
        summaries.append(summary)
        lines.append(f"| {label} | {summary['corretas_125']}/34 | {summary['corretas_0625']}/34 | {summary['corretas_ambos']}/34 | {summary['divergencias']} | {summary['pico_tensoes_uA']:.6f} |")
    lines += ['', 'As diferenças entre os passos são de classificação de janelas, não uma estimativa de erro ponto a ponto. Mudar a capacidade também muda a trajetória do sistema; estes controles não sustentam extrapolação monotônica de acertos para outros limites ou perfis.', '',
              'A comparação circuito/ideal em 90 µA avalia conjuntamente a dinâmica dos amplificadores e do limitador. A comparação ideal 90/100 µA altera a capacidade. O cálculo local, os sensores favoráveis, as guardas e o RC de comando permanecem presentes. Os resultados não isolam erros de sensores nem testam outra lei de controle.', '',
              'Evidências: ABL_ideal_90/100.cir, respectivos logs e RAW, ablacao_trajetorias.json e ablacao_janelas.csv. As oito trajetórias (136 janelas) não fazem parte das 64 trajetórias da matriz principal.']
    (ROOT/'CONTROLE_CAPACIDADE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'ablacao_resumo.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
