"""Regressao limitada da correcao estrutural dos filtros do detector."""
from pathlib import Path
import csv
import json
import sys
from analisar_etapa15 import analyze

ROOT=Path(__file__).resolve().parent

def stats(ts):
    lookup={s:{(t['x_inicial'],j):int(j not in t['janelas_falhas']) for t in ts if t['passo']==s for j in range(17)} for s in [1.25e-6,.625e-6]}
    a,b=lookup.values()
    return dict(corretas=sum(t['corretas'] for t in ts),janelas=len(ts)*17,
                corretas_ambos=sum(a[k] and b[k] for k in a),divergencias=sum(a[k]!=b[k] for k in a),
                alarmes_indevidos=sum(t['alarme_indevido'] for t in ts),
                pico_tensoes_uA=max(t['pico_tensoes_uA'] for t in ts),
                falhas_corrente=sum(t['corrente_falha_tensoes'] for t in ts),
                por_passo={str(s):sum(a.values()) for s,a in lookup.items()})

def main():
    partial='--partial' in sys.argv
    all_ts,all_rows,summary=[],[],[]
    original=json.loads((ROOT/'trajetorias.json').read_text())+json.loads((ROOT/'ablacao_trajetorias.json').read_text())
    for name in json.loads((ROOT/'lotes_filtros.json').read_text()):
        try:
            ts,rows=analyze(name)
        except (ValueError,FileNotFoundError):
            if partial:continue
            raise
        all_ts.extend(ts);all_rows.extend(rows)
        if name=='BUF_ideal90':old='ABL_ideal_90'
        else:old=name.replace('BUF_','EXP_')+'_d1'
        before=[t for t in original if t['arquivo']==old]
        assert len(before)==len(ts)==4
        summary.append(dict(arquivo=name,referencia=old,antes=stats(before),depois=stats(ts)))
    if partial:
        (ROOT/'filtros_resumo_parcial.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(json.dumps(summary,indent=2))
        return
    assert len(all_ts)==28
    (ROOT/'filtros_trajetorias.json').write_text(json.dumps(all_ts,indent=2),encoding='utf-8')
    (ROOT/'filtros_resumo.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    with (ROOT/'filtros_janelas.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    lines=['# Correção da carga entre filtros da referência', '',
           'A referência tinha um RC de 2 µs conectado diretamente a outro de 4 µs. O segundo carregava o primeiro. Na atuação, o RC de 2 µs terminava em uma entrada comportamental de alta impedância; a medição, por sua vez, excitava o RC de 4 µs por uma fonte de tensão. Assim, os dois caminhos não tinham a mesma resposta, mesmo com um atuador ideal.', '',
           'Para resistores de 1 kΩ e capacitores de 2/4 nF, a transferência dos RCs de referência antes da correção era H(s)=1/(1+10e-6 s+8e-12 s²). Dois RCs isolados dão H(s)=1/(1+6e-6 s+8e-12 s²). A diferença resulta das ligações, sem depender do modelo do amplificador. A constante do primeiro RC isolado era 2 µs, mas ele não estava isolado no circuito anterior.', '',
           'A correção acrescenta um seguidor ideal entre os RCs da referência nos canais y e D. Não muda os limiares (3 µA+10%), o tempo de confirmação, o ruído, a reserva, o alvo de 90 µA nem o limite aceito. Para uma realização física, o seguidor precisará ser implementado e caracterizado com seus erros e largura de banda.', '',
           '```mermaid','flowchart LR','  A[Comando] --> B[RC 2 µs] --> C[Atuador e medida] --> D[RC 4 µs] --> E[Comparação]',
           '  F[Referência local] --> G[RC 2 µs] --> H[Seguidor acrescentado] --> I[RC 4 µs] --> E','```','',
           '## Regressão da correção', '',
           '24 trajetórias com atuação não ideal: AB saudável/silencioso e alta demanda saudável/silencioso/atrasado/invertido; quatro com atuação ideal de 90 µA em alta demanda saudável. Todas nos dois passos e dois estados iniciais. Esta regressão não repete todas as condições da matriz original.', '',
           '| Arquivo | Acertos antes | Acertos depois | Alarmes indevidos antes → depois | Corretas depois nos dois passos | Diferenças entre passos depois |',
           '|---|---:|---:|---:|---:|---:|']
    for s in summary:
        a,b=s['antes'],s['depois']
        lines.append(f"| {s['arquivo']} | {a['corretas']}/68 | {b['corretas']}/68 | {a['alarmes_indevidos']} → {b['alarmes_indevidos']} | {b['corretas_ambos']}/34 | {b['divergencias']} |")
    lines += ['',f"Pico pelas tensões dos shunts nesta regressão: {max(t['pico_tensoes_uA'] for t in all_ts):.6f} µA. Trajetórias acima do teto: {sum(t['corrente_falha_tensoes'] for t in all_ts)}/28. Alarmes indevidos: {sum(t['alarme_indevido'] for t in all_ts)}/28 (casos sem falha e períodos anteriores às falhas temporárias; o atraso permanente não tem um período saudável inicial).", '',
              'A avaliação dos alarmes indevidos é separada da avaliação lógica. Corrigir o diagnóstico não implica eliminar as falhas lógicas em alta demanda nem validar sensores, realimentação e PCB completos. Os resultados antes da correção permanecem preservados.', '',
              'Evidências: filtros_trajetorias.json, filtros_janelas.csv e filtros_resumo.json; modelos MLC_filtros_isolados.inc e MLC_ideal_filtros_isolados.inc; decks BUF_*.cir e respectivos logs/RAW. preparar_correcao_filtros.py gera apenas a alteração de isolamento; analisar_correcao.py compara com os resultados anteriores.']
    (ROOT/'CORRECAO_FILTROS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
