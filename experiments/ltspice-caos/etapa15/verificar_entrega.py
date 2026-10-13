"""Confere contagens, CSVs, criterios e isolamento exato da alteracao."""
from pathlib import Path
import csv
import json
from preparar_correcao_filtros import buffered

ROOT=Path(__file__).resolve().parent

def main():
    totals=0
    for json_file,csv_file,count in [('trajetorias.json','resultados.csv',64),('ablacao_trajetorias.json','ablacao_janelas.csv',8),('filtros_trajetorias.json','filtros_janelas.csv',28)]:
        ts=json.loads((ROOT/json_file).read_text())
        rows=list(csv.DictReader((ROOT/csv_file).open(encoding='utf-8-sig')))
        assert len(ts)==count and len(rows)==count*17
        assert len({(t['arquivo'],t['caso']) for t in ts})==count
        for t in ts:
            subset=[r for r in rows if r['arquivo']==t['arquivo'] and int(r['caso'])==t['caso']]
            assert sorted(int(r['janela']) for r in subset)==list(range(17))
            assert sum(int(r['acerto']) for r in subset)==t['corretas']
        totals+=count
    audit=json.loads((ROOT/'auditoria_diagnostico.json').read_text())
    assert len(audit)==4
    totals+=len(audit)
    assert totals==104
    for file in ['MLC_circuito_reserva.inc','atuadores_etapa14.inc','UniversalOpAmp2.lib']:
        assert (ROOT/file).read_bytes()==(ROOT.parent/'etapa14'/file).read_bytes()
    for source,target in [('MLC_circuito_reserva.inc','MLC_filtros_isolados.inc'),('MLC_ablacao.inc','MLC_ideal_filtros_isolados.inc')]:
        assert buffered((ROOT/source).read_text())==(ROOT/target).read_text()
    ts=json.loads((ROOT/'filtros_trajetorias.json').read_text())
    faults=[t for t in ts if t['falha_coord']]
    healthy=[t for t in ts if not t['falha_coord']]
    result=dict(trajetorias=totals,janelas=totals*17,csvs_consistentes=True,originais_preservados=True,
                alteracao_restrita_ao_isolamento=True,regressao_corrente_tensoes_ok=all(not t['corrente_falha_tensoes'] for t in ts),
                regressao_corrente_resistores_ok=all(not t['corrente_falha_resistores'] for t in ts),
                regressao_corrente_sondas_ok=all(not t['corrente_falha_sondas'] for t in ts),
                regressao_sem_alarmes_indevidos=all(not t['alarme_indevido'] for t in ts),
                reserva_em_todas_falhas=all(t['latencia_reserva_us'] is not None and t['reserva_retida'] for t in faults),
                sem_reserva_em_saudaveis=all(not t['reserva_retida'] for t in healthy),
                falhas_logicas_restantes=sum(17-t['corretas'] for t in ts))
    (ROOT/'verificacao_entrega.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
