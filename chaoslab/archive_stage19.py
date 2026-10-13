"""Publish portable compact evidence only after the registered suite completes."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
from chaoslab.storage import ROOT, _atomic
from chaoslab.stage19 import OUT, write_json, signature


def main():
    plan = json.loads((OUT/"plano_registrado.json").read_text(encoding="utf-8"))
    index = json.loads((OUT/"resultados.json").read_text(encoding="utf-8"))
    registered = {c["name"]:c for c in plan["cases"]}
    if set(r["name"] for r in index) != set(registered):
        raise ValueError("O lote ainda não corresponde integralmente ao plano registrado.")
    current = hashlib.sha256((ROOT/"chaoslab/core.py").read_bytes()).hexdigest()
    if current != plan["core_source_sha256"]:
        raise ValueError("O núcleo mudou; a proveniência exige nova revisão.")
    archive = OUT/"runs"
    archive.mkdir(exist_ok=True)
    records, checks, digests = [], [], {}
    for record in index:
        name = record["name"]
        original = Path(record["path"]).resolve()
        if not original.is_relative_to((ROOT/"chaoslab/results").resolve()):
            raise ValueError("Fonte fora do armazenamento de resultados esperado.")
        packed = original.read_bytes()
        payload = gzip.decompress(packed)
        result = json.loads(payload)
        cfg, summary = result["config"], result["summary"]
        expected_count = cfg["trajectories"]*cfg["windows"]
        if result.get("status") != "complete" or result["suite_signature"] != signature(registered[name]):
            raise ValueError(f"Resultado incompleto ou configuração divergente: {name}")
        if result["core_source_sha256"] != current:
            raise ValueError(f"Hash do núcleo divergente: {name}")
        windows = result["windows"]
        if len(windows) != expected_count or summary["total_windows"] != expected_count:
            raise ValueError(f"Contagem de janelas divergente: {name}")
        keys = {(w["trajectory"],w["window"]) for w in windows}
        if len(keys) != expected_count:
            raise ValueError(f"Janelas repetidas: {name}")
        recomputed = 0
        for w in windows:
            margin = w["min"] if w["expected"] else -w["max"]
            good = margin > 0
            if good != w["correct"] or margin != w["margin"] or w["expected"] != int(w["input"] == 3):
                raise ValueError(f"Classificação inconsistente: {name}")
            recomputed += good
        if recomputed != summary["correct_windows"] or recomputed != sum(p["correct_windows"] for p in result["per_trajectory"]):
            raise ValueError(f"Acertos inconsistentes: {name}")
        budget_applies = cfg["profile"] != "unlimited"
        if budget_applies and summary["peak_current_uA"] > 90+1e-9:
            raise ValueError(f"Orçamento algébrico excedido: {name}")
        if summary["peak_e_uA"] > 5+1e-9:
            raise ValueError(f"Reserva E excedida: {name}")
        destination = archive/(name+".json.gz")
        _atomic(destination,packed)
        if destination.read_bytes() != packed:
            raise IOError("Falha ao verificar arquivo portátil")
        portable = dict(record, path=destination.relative_to(ROOT).as_posix(),
                        sha256_gzip=hashlib.sha256(packed).hexdigest(),
                        sha256_json=hashlib.sha256(payload).hexdigest(),bytes=len(packed))
        records.append(portable)
        digests[name] = result["validation"]["state_digest"]
        checks.append(dict(name=name,windows=expected_count,correct_recomputed=recomputed,
                           budget_applies=budget_applies,budget_ok=not budget_applies or summary["peak_current_uA"] <=90+1e-9))
    healthy_equal = len({digests[f"ensemble_healthy_{s}"] for s in ("off","quota","effective")}) == 1
    cancellation_equal = digests["ablation_nominal"] == digests["ablation_unlimited"]
    if not healthy_equal or not cancellation_equal:
        raise ValueError("Invariante de referência/observação não passou no lote completo.")
    write_json(OUT/"resultados_portateis.json",records)
    write_json(OUT/"VERIFICACAO_ENTREGA.json",dict(
        cases=len(checks),windows=sum(c["windows"] for c in checks),
        portable_bytes=sum(r["bytes"] for r in records),core_sha256=current,
        healthy_observer_state_bitwise_equal=healthy_equal,
        nominal_unlimited_state_bitwise_equal=cancellation_equal,
        classifications_recomputed=True,all_registered_cases_complete=True,
        note="Checks verify serialized consistency and algebraic bounds, not physical hardware or between-grid extrema.",
        checks=checks))
    print(json.dumps({"archived_cases":len(checks),"windows":sum(c["windows"] for c in checks),
                      "megabytes":sum(r["bytes"] for r in records)/1e6}))


if __name__ == "__main__":
    main()
