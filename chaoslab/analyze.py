"""Audit and report the complete registered Stage 19 suite without rerunning it.

The statistical unit is one trajectory (all its consecutive windows together),
not an individual logical window. Run ``python -m chaoslab.analyze --self-test``
for synthetic checks only. Default invocation publishes nothing until all
registered results, their hashes, and every logical-window row have passed audit.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np

from chaoslab.storage import ROOT, _atomic, load_result

OUT = ROOT / "experiments" / "ltspice-caos" / "etapa19"
BOOTSTRAP_SEED = 19300
BOOTSTRAP_REPLICATES = 5000
SCHEMA = "chaoslab-stage19-analysis-v1"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _signature(case: dict) -> str:
    return hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()


def _finite(value: Any, trail="result") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"Nonfinite value at {trail}")
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{trail}[{index}]")


def audit_result(result: dict, case: dict) -> dict:
    """Check logical rows and their aggregates independently of the saved summary."""
    name = case["name"]
    if result.get("status") not in ("complete", "completed"):
        raise ValueError(f"{name}: result is not complete")
    if result.get("config") != case["config"]:
        raise ValueError(f"{name}: configuration differs from the registered plan")
    cfg, summary = result["config"], result["summary"]
    count, windows = cfg["trajectories"], cfg["windows"]
    rows = result["windows"]
    if len(rows) != count * windows:
        raise ValueError(f"{name}: incomplete window table")
    sequence = result["validation"]["input_sequence"]
    if len(sequence) != windows:
        raise ValueError(f"{name}: incomplete input sequence")
    seen, correct = set(), np.zeros(count, dtype=np.int64)
    for row in rows:
        j, w = row["trajectory"], row["window"]
        if type(j) is not int or type(w) is not int or not (0 <= j < count and 0 <= w < windows):
            raise ValueError(f"{name}: invalid trajectory/window identity")
        if (j, w) in seen:
            raise ValueError(f"{name}: repeated logical window {(j,w)}")
        seen.add((j, w))
        expected = int(sequence[w] == 3)
        if row["input"] != sequence[w] or row["expected"] != expected:
            raise ValueError(f"{name}: truth table/input mismatch at {(j,w)}")
        if abs(row["window_start_s"] - (w*.05+.03)) > 1e-12 or abs(row["window_end_s"] - (w*.05+.049)) > 1e-12:
            raise ValueError(f"{name}: wrong logical interval at {(j,w)}")
        if row["min"] > row["max"]:
            raise ValueError(f"{name}: inverted extrema at {(j,w)}")
        margin = row["min"] if expected else -row["max"]
        if abs(row["margin"]-margin) > 1e-12 or type(row["correct"]) is not bool or row["correct"] != (margin > 0):
            raise ValueError(f"{name}: strict logical criterion mismatch at {(j,w)}")
        correct[j] += int(row["correct"])
    per = sorted(result["per_trajectory"], key=lambda r: r["trajectory"])
    if len(per) != count or [r["trajectory"] for r in per] != list(range(count)):
        raise ValueError(f"{name}: incomplete per-trajectory table")
    for j, row in enumerate(per):
        if row["total_windows"] != windows or row["correct_windows"] != int(correct[j]):
            raise ValueError(f"{name}: per-trajectory count mismatch")
    if summary["total_windows"] != len(rows) or summary["planned_windows"] != len(rows) or summary["correct_windows"] != int(correct.sum()):
        raise ValueError(f"{name}: summary count mismatch")
    for field, indicator in (("alarm_trajectories", "alarm"),
                             ("false_alarm_trajectories", "false_alarm"),
                             ("detected_fault_trajectories", "detected_fault"),
                             ("alarms_after_fault_trajectories", "alarm_after_fault"),
                             ("fault_trajectories", "fault_injected")):
        if summary[field] != sum(bool(r[indicator]) for r in per):
            raise ValueError(f"{name}: {field} aggregate mismatch")
    if "alarms_boundary_before_fault_trajectories" in summary:
        if summary["alarms_boundary_before_fault_trajectories"] != sum(bool(r.get("alarm_boundary_before_fault")) for r in per):
            raise ValueError(f"{name}: boundary-alarm aggregate mismatch")
    for row in per:
        if row["detected_fault"] and (not row["fault_injected"] or not row["alarm"] or row["false_alarm"]
                                      or row.get("detection_latency_us") is None or row["detection_latency_us"]<0):
            raise ValueError(f"{name}: inconsistent fault-detection qualification")
    timing = result["timing"]
    if timing["steps"] != timing["planned_steps"]:
        raise ValueError(f"{name}: unfinished fixed-grid trajectory")
    h = cfg["dt_us"]*1e-6
    if abs(timing["simulated_seconds_per_trajectory"]-timing["steps"]*h) > 1e-10:
        raise ValueError(f"{name}: time/grid mismatch")
    if timing["simulated_seconds_per_trajectory"] < windows*.05-1e-10:
        raise ValueError(f"{name}: final time below the planned duration")
    if abs(summary["peak_current_uA"]-max(r["peak_current_uA"] for r in per)) > 1e-8:
        raise ValueError(f"{name}: peak-current aggregate mismatch")
    if not result["validation"].get("fixed_step") or result["validation"].get("physical_hardware_model"):
        raise ValueError(f"{name}: unexpected solver/model declaration")
    _finite(result, name)
    return dict(case=name, trajectories=count, windows=len(rows), correct=int(correct.sum()),
                logical_rows_verified=len(rows), time_grid_verified=True)


def load_complete_suite(folder: Path = OUT) -> tuple[dict, dict[str, dict], dict]:
    """Read/audit first. This function never writes a partial or final report."""
    plan_path = folder/"plano_registrado.json"
    portable = (folder/"resultados_portateis.json").exists()
    records_path = folder/("resultados_portateis.json" if portable else "resultados.json")
    if not plan_path.exists() or not records_path.exists():
        raise ValueError("Lote ainda incompleto: plano_registrado.json/resultados.json ausente. Nenhum relatorio alterado.")
    plan, records = _json(plan_path), _json(records_path)
    if isinstance(records,dict):
        records=records.get("cases",records.get("results",records.get("records")))
        if not isinstance(records,list):
            raise ValueError("Registro portatil sem lista cases/results/records")
    cases = plan["cases"]
    expected_cases=len(cases)
    expected_windows=sum(c["config"]["trajectories"]*c["config"]["windows"] for c in cases)
    if not expected_cases or plan["total_cases"] != expected_cases or plan["planned_windows"] != expected_windows:
        raise ValueError("Contagens do plano inconsistentes")
    if len(records) != expected_cases:
        raise ValueError(f"Aguardar os {expected_cases} ensaios: apenas {len(records)} registros finais. Nenhum relatorio alterado.")
    planned = {c["name"]: c for c in cases}
    if len(planned) != expected_cases or len({r["name"] for r in records}) != expected_cases or {r["name"] for r in records} != set(planned):
        raise ValueError("Ensaios repetidos, desconhecidos ou ausentes")
    progress_path = folder/"progresso.json"
    if progress_path.exists() and _json(progress_path).get("status") not in ("complete", "completed"):
        raise ValueError("O gerenciador ainda nao confirmou a conclusao integral do lote")
    core_path = ROOT/"chaoslab"/"core.py"
    if sha256(core_path) != plan["core_source_sha256"]:
        raise ValueError("O core atual difere do hash registrado; revisar a proveniencia antes de publicar")
    results, sources, audits = {}, [], []
    for record in sorted(records, key=lambda r: r["name"]):
        name, case = record["name"], planned[record["name"]]
        if record["signature"] != _signature(case):
            raise ValueError(f"{name}: registry signature mismatch")
        path = Path(record["path"])
        if not path.is_absolute():
            path=ROOT/path
        result = load_result(path)
        if result.get("name") != name or result.get("group") != case["group"] or result.get("suite_signature") != _signature(case):
            raise ValueError(f"{name}: saved result identity/signature mismatch")
        if result.get("core_source_sha256") != plan["core_source_sha256"] or result["validation"]["core_version"] != plan["core_version"]:
            raise ValueError(f"{name}: mixed core revisions")
        for key in ("config", "summary", "timing", "validation"):
            if record[key] != result[key]:
                raise ValueError(f"{name}: final registry and full result disagree on {key}")
        metadata_path = Path(str(path)[:-len(".json.gz")]+".meta.json")
        metadata = _json(metadata_path) if metadata_path.exists() else {}
        with gzip.open(path, "rb") as stream:
            unpacked_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        expected_json_hash=record.get("sha256_json",metadata.get("sha256_json"))
        if expected_json_hash is None:
            raise ValueError(f"{name}: missing reference hash for the saved JSON payload")
        if unpacked_hash != expected_json_hash:
            raise ValueError(f"{name}: saved JSON payload hash mismatch")
        compressed_hash=sha256(path)
        if record.get("sha256_gzip") is not None and compressed_hash!=record["sha256_gzip"]:
            raise ValueError(f"{name}: archive hash mismatch")
        audits.append(audit_result(result, case))
        results[name] = result
        sources.append(dict(case=name, path=str(path), bytes=path.stat().st_size,
                            sha256_gzip=compressed_hash, sha256_json=unpacked_hash,
                            suite_signature=_signature(case)))
    if sum(a["windows"] for a in audits) != expected_windows:
        raise ValueError("Audited total-window count mismatch")
    provenance = dict(plan_path=str(plan_path), plan_sha256=sha256(plan_path),
                      results_registry_path=str(records_path), portable_registry=portable,
                      results_registry_sha256=sha256(records_path), core_source_sha256=plan["core_source_sha256"],
                      core_version=plan["core_version"], registered_python=plan.get("python"),
                      registered_numpy=plan.get("numpy"), analysis_python=sys.version,
                      analysis_numpy=np.__version__, analyzer_sha256=sha256(Path(__file__)),
                      sources=sources, audits=audits)
    return plan, results, provenance


def quantiles(values) -> dict:
    array = np.asarray([v for v in values if v is not None], dtype=float)
    if not len(array):
        return dict(n=0, min=None, q1=None, median=None, q3=None, max=None)
    if not np.isfinite(array).all():
        raise ValueError("Nonfinite quantile input")
    vals = np.quantile(array, [0., .25, .5, .75, 1.])
    return dict(n=len(array), **{key:float(value) for key,value in zip(("min","q1","median","q3","max"),vals)})


def cluster_bootstrap(a: np.ndarray, b: np.ndarray, mask: np.ndarray | None = None,
                      replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED) -> dict:
    """Paired percentile intervals; one resampled index includes its whole row."""
    a, b = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    if a.ndim != 2 or a.shape != b.shape or not a.shape[0]:
        raise ValueError("Expected matched trajectory x window matrices")
    mask = np.ones(a.shape, dtype=bool) if mask is None else np.broadcast_to(mask, a.shape)
    totals = mask.sum(axis=1).astype(float)
    if totals.sum() == 0:
        raise ValueError("Empty bootstrap subgroup")
    numerators = np.column_stack(((a & mask).sum(axis=1), (b & mask).sum(axis=1),
                                  ((~a) & b & mask).sum(axis=1), (a & (~b) & mask).sum(axis=1)))
    rng = np.random.default_rng(seed)
    samples = np.empty((replicates, 4), dtype=float)
    for left in range(0, replicates, 128):
        right = min(replicates, left+128)
        indices = rng.integers(0, a.shape[0], size=(right-left, a.shape[0]))
        denominator = totals[indices].sum(axis=1)
        if np.any(denominator == 0):
            raise ValueError("Bootstrap produced empty cluster subgroup")
        samples[left:right] = numerators[indices].sum(axis=1)/denominator[:,None]
    def ci(column):
        values = np.quantile(column, [.025,.975])*100
        return [float(values[0]), float(values[1])]
    return dict(method="paired trajectory-cluster percentile bootstrap", clusters=a.shape[0],
                replicates=replicates, seed=seed, coverage=.95,
                baseline_rate_percent_ci95=ci(samples[:,0]), candidate_rate_percent_ci95=ci(samples[:,1]),
                delta_percentage_points_ci95=ci(samples[:,1]-samples[:,0]),
                recovered_percentage_points_ci95=ci(samples[:,2]), regressed_percentage_points_ci95=ci(samples[:,3]),
                interpretation="Descriptive sensitivity to the sampled initial conditions, conditional on the shared deterministic sequence/phases. Not independent-window or hardware-reliability confidence.")


def _window_matrix(result: dict) -> tuple[np.ndarray, np.ndarray]:
    cfg = result["config"]
    matrix = np.zeros((cfg["trajectories"],cfg["windows"]), dtype=bool)
    code = np.full(matrix.shape, -1, dtype=int)
    for row in result["windows"]:
        matrix[row["trajectory"],row["window"]] = row["correct"]
        code[row["trajectory"],row["window"]] = row["input"]
    return matrix, code


def paired(baseline: dict, candidate: dict, *, bootstrap=False, allowed_config_differences=None) -> dict:
    """Require identical ICs and window identities before attributing changes."""
    for key in ("trajectories", "windows", "seed", "sequence"):
        if baseline["config"][key] != candidate["config"][key]:
            raise ValueError(f"Unmatched paired configuration: {key}")
    if allowed_config_differences is not None:
        differences={key for key in set(baseline["config"])|set(candidate["config"])
                     if baseline["config"].get(key)!=candidate["config"].get(key)}
        unexpected=differences-set(allowed_config_differences)
        if unexpected:
            raise ValueError(f"Confounded paired comparison; unexpected configuration changes: {sorted(unexpected)}")
    left = {(r["trajectory"],r["window"]):r for r in baseline["windows"]}
    right = {(r["trajectory"],r["window"]):r for r in candidate["windows"]}
    if set(left) != set(right) or len(left) != len(baseline["windows"]) or len(right) != len(candidate["windows"]):
        raise ValueError("Unmatched/duplicated window identities")
    for key, row in left.items():
        for field in ("input","expected","window_start_s","window_end_s"):
            if row[field] != right[key][field]:
                raise ValueError(f"Unmatched window {key}, field {field}")
    initial = lambda result: sorted((r["trajectory"],r["initial_x"],r["initial_y"]) for r in result["per_trajectory"])
    if initial(baseline) != initial(candidate):
        raise ValueError("Unmatched initial conditions")
    a, codes = _window_matrix(baseline)
    b, candidate_codes = _window_matrix(candidate)
    if not np.array_equal(codes, candidate_codes):
        raise ValueError("Unmatched input matrix")
    def counts(mask):
        count = int(np.count_nonzero(mask))
        aa, bb = a[mask], b[mask]
        recovered = int(np.count_nonzero((~aa)&bb))
        regressed = int(np.count_nonzero(aa&(~bb)))
        return dict(windows=count, baseline_correct=int(aa.sum()), candidate_correct=int(bb.sum()),
                    recovered=recovered, regressed=regressed, net=recovered-regressed,
                    both_correct=int(np.count_nonzero(aa&bb)), both_failed=int(np.count_nonzero((~aa)&(~bb))),
                    discordant=recovered+regressed,
                    delta_percentage_points=100*(recovered-regressed)/count if count else None)
    result = dict(baseline=baseline["name"], candidate=candidate["name"],
                  **counts(np.ones(a.shape,dtype=bool)),
                  by_input={f"{code:02b}":counts(codes==code) for code in range(4)})
    if bootstrap:
        if a.shape[0] != 500:
            raise ValueError("Stage 19 ensemble intervals require exactly 500 trajectory clusters")
        result["bootstrap"] = cluster_bootstrap(a,b)
        for code in range(4):
            result["by_input"][f"{code:02b}"]["bootstrap"] = cluster_bootstrap(a,b,codes==code)
    return result


def fault_statistics(result: dict) -> dict:
    per = result["per_trajectory"]
    detected = [r for r in per if r["detected_fault"]]
    causes = Counter(c for r in per if r["alarm"] for c in r.get("alarm_causes",[]))
    return dict(case=result["name"], policy=result["config"]["policy"], detector=result["config"]["detector"],
                fault=result["config"]["fault"], corner=result["config"]["corner"],
                trajectories=len(per), injected=sum(bool(r["fault_injected"]) for r in per),
                detected=len(detected), false_before_or_healthy=sum(bool(r["false_alarm"]) for r in per),
                before_fault=sum(str(r.get("alarm_timing","")).startswith("pre_fault") for r in per),
                pre_fault_reason_at_boundary=sum(bool(r.get("alarm_boundary_before_fault")) for r in per),
                late=sum(bool(r["alarm_after_fault"]) for r in per),
                alarm_causes=dict(causes), alarm_timings=dict(Counter(r.get("alarm_timing","unknown") for r in per)),
                detection_latency_us=quantiles(r.get("detection_latency_us") for r in detected),
                latency_from_harm_us=quantiles(r.get("latency_from_harm_us") for r in detected),
                fallback_after_alarm_us=quantiles(r["fallback_time_us"]-r["alarm_time_us"] for r in per
                    if r.get("fallback_time_us") is not None and r.get("alarm_time_us") is not None),
                grant_divergence_observed=sum(r.get("harm_start_us") is not None for r in per),
                alarm_before_grant_divergence=sum(r.get("latency_from_harm_us") is not None and r["latency_from_harm_us"]<0 for r in detected),
                harm_field_meaning="Legacy field name: first absolute useful-grant divergence versus fault-free quota, OR invalid basic message. A larger grant can be beneficial; this is not necessarily damage or deficit.",
                correct_windows=result["summary"]["correct_windows"], total_windows=result["summary"]["total_windows"])


def summary_row(result: dict) -> dict:
    cfg, s = result["config"], result["summary"]
    return dict(case=result["name"], group=result["group"], dt_us=cfg["dt_us"], trajectories=cfg["trajectories"],
                windows_per_trajectory=cfg["windows"], profile=cfg["profile"], policy=cfg["policy"],
                detector=cfg["detector"], fallback=cfg["fallback"], fallback_policy=cfg.get("fallback_policy","common"),
                fault=cfg["fault"], corner=cfg["corner"], total_windows=s["total_windows"], correct_windows=s["correct_windows"],
                correct_percent=100*s["correct_windows"]/s["total_windows"],
                false_alarm_trajectories=s["false_alarm_trajectories"], detected_fault_trajectories=s["detected_fault_trajectories"],
                fault_trajectories=s["fault_trajectories"], late_alarm_trajectories=s["alarms_after_fault_trajectories"],
                peak_current_uA=s["peak_current_uA"], peak_e_uA=s["peak_e_uA"],
                budget_applies=cfg["profile"]!="unlimited", budget_ok=result["validation"]["budget_ok"],
                residual_y_rms_uA=s["residual_y_rms_uA"], residual_d_rms_uA=s["residual_d_rms_uA"],
                mean_trajectory_residual_y_rms_uA=float(np.mean([r["residual_y_rms_uA"] for r in result["per_trajectory"]])),
                mean_trajectory_residual_d_rms_uA=float(np.mean([r["residual_d_rms_uA"] for r in result["per_trajectory"]])),
                g_total_variation_per_s=s["g_total_variation_per_s"], reserve_fraction=s["reserve_fraction"],
                elapsed_s=result["timing"]["elapsed_s"], state_digest=result["validation"]["state_digest"])


def analyze(results: dict[str,dict], plan: dict, provenance: dict) -> dict:
    comparisons = {}
    def compare(label, left, right, bootstrap=False, allowed=("detector",)):
        comparisons[label] = paired(results[left],results[right],bootstrap=bootstrap,allowed_config_differences=allowed)
    for fault in ("healthy","bias"):
        for base,candidate in (("off","quota"),("off","effective"),("quota","effective")):
            compare(f"{fault}_{base}_to_{candidate}",f"ensemble_{fault}_{base}",f"ensemble_{fault}_{candidate}",True)
    compare("healthy_l2_to_common","ensemble_healthy_off","ensemble_healthy_common",True,allowed=("policy",))
    for detector in ("off","quota","effective"):
        left,right=f"ensemble_healthy_{detector}",f"ensemble_bias_{detector}"
        compare(f"fault_impact_{detector}",left,right,True,allowed=("fault",))
        # These pairs measure the bias effect, not a detector treatment effect.
        pair=comparisons[f"fault_impact_{detector}"]
        pair["interpretation"]="Same detector/policy, fault-free baseline versus +12-uA quota bias."
        before=lambda result: sorted((row for row in result["windows"] if row["window_end_s"]<=.34335),key=lambda r:(r["trajectory"],r["window"]))
        pair["pre_injection_windows"]=len(before(results[left]))
        pair["pre_injection_windows_identical"]=before(results[left])==before(results[right])
        if not pair["pre_injection_windows_identical"]:
            raise ValueError(f"{detector}: healthy/bias trajectories differ before injection; causal attribution refused")
    for detector in ("quota","effective"):
        compare(f"fallback_{detector}",f"fault_bias_{detector}",f"matched_bias_{detector}",allowed=("fallback_policy",))
    for fault in ("bias","replay","stale","dropout","double","starve"):
        compare(f"fault_{fault}_quota_to_effective",f"fault_{fault}_quota",f"fault_{fault}_effective")
    for policy in ("common","l2"):
        for corner in ("plus","minus"):
            compare(f"corner_{policy}_{corner}_quota_to_effective",f"corner_{policy}_{corner}_quota",f"corner_{policy}_{corner}_effective")
    for left,right in (("nominal","unlimited"),("nominal","ideal"),("ideal","sensors"),("sensors","coordinator"),("coordinator","actuator")):
        compare(f"ablation_{left}_to_{right}",f"ablation_{left}",f"ablation_{right}",allowed=("profile",))
    refinement = {}
    for detector in ("quota","effective"):
        names=[f"refine_{detector}_{step:g}" for step in (5.,2.5,1.25)]
        first=paired(results[names[0]],results[names[1]],allowed_config_differences=("dt_us",))
        second=paired(results[names[1]],results[names[2]],allowed_config_differences=("dt_us",))
        matrices=[_window_matrix(results[name])[0] for name in names]
        stable=(matrices[0]==matrices[1])&(matrices[1]==matrices[2])
        refinement[detector]=dict(cases=names, steps_us=[5.,2.5,1.25], windows_per_step=matrices[0].size,
            correct=[int(m.sum()) for m in matrices], successive_pairs=[first,second],
            correct_all_three=int(np.logical_and.reduce(matrices).sum()),
            failed_all_three=int(np.logical_and.reduce([~m for m in matrices]).sum()),
            classifications_identical_all_three=int(stable.sum()), classifications_changed=int((~stable).sum()),
            false_alarms=[results[name]["summary"]["false_alarm_trajectories"] for name in names],
            residual_y_rms_uA=[results[name]["summary"]["residual_y_rms_uA"] for name in names],
            residual_d_rms_uA=[results[name]["summary"]["residual_d_rms_uA"] for name in names],
            g_total_variation_per_s=[results[name]["summary"]["g_total_variation_per_s"] for name in names],
            convergence_established=False,
            interpretation="Logical disagreements remain" if not stable.all() else "No disagreement in these sampled windows; this alone does not establish numerical convergence.")
    rows=[summary_row(results[name]) for name in sorted(results)]
    bounded=[r for r in rows if r["budget_applies"]]
    budget_failures=[r["case"] for r in bounded if r["peak_current_uA"]>90+1e-9 or r["budget_ok"] is not True]
    unlimited=[r for r in rows if not r["budget_applies"]]
    ensemble_rates={}
    for name,result in results.items():
        if result["group"]=="ensemble_10000":
            matrix,_=_window_matrix(result)
            ensemble_rates[name]=cluster_bootstrap(matrix,matrix)
    nominal,unlimited_result=results["ablation_nominal"],results["ablation_unlimited"]
    identity=dict(same_final_state=nominal["validation"]["final_state_sha256"]==unlimited_result["validation"]["final_state_sha256"],
                  same_windows=nominal["windows"]==unlimited_result["windows"],
                  meaning="Analytical perturbation cancellation reduces the unlimited plant RHS to the nominal RHS at every RK stage; it is an algebraic reference, not a finite-budget implementation.")
    passive_names=[f"ensemble_healthy_{d}" for d in ("off","quota","effective")]
    passive=dict(cases=passive_names,
                 no_fallback_selected=all(results[n]["summary"]["reserve_fraction"]==0 for n in passive_names),
                 same_final_state= len({results[n]["validation"]["final_state_sha256"] for n in passive_names})==1,
                 same_relevant_state_digest=len({results[n]["validation"]["state_digest"] for n in passive_names})==1,
                 same_window_tables=all(results[n]["windows"]==results[passive_names[0]]["windows"] for n in passive_names[1:]),
                 meaning="Checks final states and complete logical-window tables for the three healthy cohorts. Full continuous trajectories are not stored; fallback activation would be an actual control change, not an observer-step effect.")
    ensemble_results=[r for r in results.values() if r["group"]=="ensemble_10000"]
    legacy_results=[r for r in results.values() if r["group"]!="ensemble_10000"]
    return dict(schema=SCHEMA, created_utc=datetime.now(timezone.utc).isoformat(), status="complete",
        counts=dict(cases=len(results), trajectories=sum(r["config"]["trajectories"] for r in results.values()),
                    windows=sum(r["summary"]["total_windows"] for r in results.values()),
                    ensemble_cases=len(ensemble_results), ensemble_windows=sum(r["summary"]["total_windows"] for r in ensemble_results),
                    legacy_cases=len(legacy_results), legacy_windows=sum(r["summary"]["total_windows"] for r in legacy_results),
                    cohort_description="Repeated paired executions of 500 trajectories x 20 windows (10,000 each), plus legacy executions of 2 x 17. Reused ICs/inputs are paired observations, not independent tests per window."),
        provenance=provenance, bootstrap=dict(seed=BOOTSTRAP_SEED,replicates=BOOTSTRAP_REPLICATES,clusters=500,
            unit="trajectory including all consecutive windows",interpretation="Descriptive initial-condition sensitivity only; common phases/inputs and two prescribed endpoint ICs prevent a hardware reliability interpretation."),
        rows=rows, ensemble_rate_intervals=ensemble_rates, comparisons=comparisons, refinement=refinement,
        fault_matrix=[fault_statistics(results[name]) for name in sorted(results) if results[name]["group"]=="fault_matrix"],
        corners=[fault_statistics(results[name]) for name in sorted(results) if results[name]["group"]=="corners"],
        ablations=[r for r in rows if r["group"]=="ablation"], nominal_unlimited_identity=identity,
        healthy_observer_comparison=passive,
        fallback=[fault_statistics(results[name]) for name in sorted(results) if results[name]["group"]=="fallback"],
        current=dict(bounded_cases=len(bounded), bounded_trajectories=sum(r["trajectories"] for r in bounded),
                     maximum_bounded_uA=max(r["peak_current_uA"] for r in bounded), failed_cases=budget_failures,
                     unlimited_exempt_cases=[dict(case=r["case"],peak_current_uA=r["peak_current_uA"]) for r in unlimited],
                     meaning="Algebraic projection/finite-budget mathematical allocation only. No physical 90-uA or chip/PCB validation."),
        numerical_convergence_established=False,
        limitations=plan.get("limitations",[])+[
            "Window extrema are sampled at fixed-grid nodes with linear interpolation only at interval boundaries; between-node sign crossings may be missed.",
            "RK4 advances the plant while sampled controls and RC blocks use explicit ZOH splitting; the complete method is not globally fourth order.",
            "The 10,000-window cohorts use the coarse 5-us step; their counts are exploratory until smaller-step ensemble checks support stability.",
            "The healthy L2/common comparison changes both allocation policy and its derived coordinator delay/filter: L2 uses 5/10 us, common uses 20/50 us. It compares complete configurations, not the isolated allocation rule.",
            "Unlimited cancels perturbations analytically at every RK4 substage; ideal applies a finite-budget current sampled at the start of the step and held. Their difference mixes capacity/policy with current-update timing and does not isolate the budget alone.",
            "The coordinator/off to actuator/off ablation identifies the incremental effect of this mathematical actuator surrogate, not actual hardware latency.",
            "Detector differences may change fallback timing and the chaotic trajectory. Logical recovery requires paired recovered AND regressed windows, not detection counts alone.",
            "The legacy harm_start field marks first absolute useful-grant divergence OR an invalid basic message, not necessarily a deficit: a positive grant change may be beneficial. Negative latency_from_harm means alarm before that marker.",
            "ChaosLab summary residual RMS pools squared residuals across trajectories. Stage 18 reports the arithmetic mean of per-trajectory RMS. Both aggregates are supplied in resumo.csv and must not be equated.",
            "Direct count comparisons with the old 198/272 matrix are invalid because the cohorts and numerical models differ."])


def _format_quantiles(data: dict) -> str:
    if not data["n"]:
        return "sem observacao"
    return f"n={data['n']}; min={data['min']:.3f}, Q1={data['q1']:.3f}, mediana={data['median']:.3f}, Q3={data['q3']:.3f}, max={data['max']:.3f} us"


def report_text(analysis: dict) -> str:
    rows={r["case"]:r for r in analysis["rows"]}
    counts=analysis["counts"]
    lines=["ETAPA 19 — CHAOSLAB: CONCESSAO EFETIVA, COTAS E PASSOS FIXOS", "",
        f"Concluido: {analysis['counts']['cases']} ensaios e {analysis['counts']['windows']:,} janelas auditadas (separador de milhar: virgula).",
        "Cada conjunto grande tem 500 trajetorias x 20 janelas consecutivas = 10.000 janelas por execucao.",
        f"Sao {counts['ensemble_cases']} execucoes pareadas desse conjunto: {counts['ensemble_windows']} observacoes; os outros {counts['legacy_cases']} ensaios somam {counts['legacy_windows']} janelas.",
        "As condicoes iniciais e entradas sao repetidas entre tratamentos. O total nao representa testes independentes por janela, nem uma unica trajetoria de 500 segundos.", "",
        "CONCLUSOES DETERMINADAS PELOS DADOS", ""]
    for fault,label in (("healthy","Sem falha injetada"),("bias","Com vies de +12 uA em favor de Y")):
        item=analysis["comparisons"][f"{fault}_quota_to_effective"]
        q,e=rows[item["baseline"]],rows[item["candidate"]]
        ci=item["bootstrap"]["delta_percentage_points_ci95"]
        lines += [f"{label}: fiscal de cotas {q['correct_windows']}/{q['total_windows']}; concessao efetiva {e['correct_windows']}/{e['total_windows']}.",
                  f"A troca recuperou {item['recovered']} janelas e introduziu {item['regressed']} novas falhas; saldo {item['net']:+d} ({item['delta_percentage_points']:+.3f} pontos percentuais).",
                  f"IC95 descritivo do saldo, bootstrap por trajetoria: [{ci[0]:+.3f}, {ci[1]:+.3f}] pontos percentuais.",
                  f"Alarmes indevidos: cotas {q['false_alarm_trajectories']}/{q['trajectories']}; efetiva {e['false_alarm_trajectories']}/{e['trajectories']}."]
        lines.append(f"Residuos RMS agrupados: Y {q['residual_y_rms_uA']:.6f} -> {e['residual_y_rms_uA']:.6f} uA; D {q['residual_d_rms_uA']:.6f} -> {e['residual_d_rms_uA']:.6f} uA. TV(g)/s {q['g_total_variation_per_s']:.6f} -> {e['g_total_variation_per_s']:.6f}, excluindo os primeiros 30 ms.")
        if item["regressed"]:
            lines.append("O saldo agregado nao elimina as regressoes individuais; nao ha dominancia janela a janela.")
        if item["discordant"]==0:
            lines.append("Os tratamentos coincidiram na classificacao de todas as janelas deste conjunto; nenhum efeito logico foi observado nessa comparacao.")
        elif ci[0] <= 0 <= ci[1]:
            lines.append("O intervalo descritivo do saldo inclui zero; este conjunto nao separa claramente o efeito agregado de sua sensibilidade as condicoes iniciais.")
        both=item["by_input"]["11"]
        lines += [f"Entrada 11: {both['baseline_correct']} -> {both['candidate_correct']} de {both['windows']}; recuperadas {both['recovered']}, novas falhas {both['regressed']}.",""]
    for detector,label in (("quota","cotas"),("effective","concessao efetiva")):
        corners=[r for r in analysis["corners"] if r["detector"]==detector]
        false=sum(r["false_before_or_healthy"] for r in corners)
        total=sum(r["trajectories"] for r in corners)
        lines.append(f"Cantos de tolerancia, {label}: {false}/{total} trajetorias saudaveis com alarme indevido.")
        if false:
            lines.append(f"O fiscal de {label} ainda nao esta qualificado para essas tolerancias.")
    lines.append("")
    for detector,label in (("quota","cotas"),("effective","concessao efetiva")):
        item=analysis["refinement"][detector]
        last=item["successive_pairs"][-1]
        lines.append(f"Refinamento, {label}: {item['correct']} acertos de {item['windows_per_step']} nos passos {item['steps_us']} us. Entre as duas malhas mais finas, {last['discordant']}/{last['windows']} classificacoes mudaram ({last['recovered']} recuperadas e {last['regressed']} novas falhas).")
    lines += ["A convergencia numerica global permanece nao estabelecida. Os conjuntos de 10.000 janelas usam 5 us e sao exploratorios.",
              "Passos fixos impedem que observadores passivos escolham o passo do integrador; continuam existindo erros de discretizacao, amostragem e separacao dos blocos.",
              "O laboratorio nao demonstra que uma falha de recuperacao seja exclusivamente da equacao ou exclusivamente de atraso fisico.",""]
    passive=analysis["healthy_observer_comparison"]
    lines += [f"Controle de observacao saudavel (off/cotas/efetiva): reserva nunca selecionada={passive['no_fallback_selected']}; estados finais identicos={passive['same_final_state']}; tabelas completas de janelas identicas={passive['same_window_tables']}.",
              "A verificacao salva cobre estados finais e janelas. A desconexao de observadores passivos do passo numerico decorre tambem da arquitetura e dos testes do motor; ativar a reserva e uma mudanca real de controle.",""]
    if passive["no_fallback_selected"] and not (passive["same_final_state"] and passive["same_window_tables"]):
        lines += ["FALHA DE CONTROLE: sem selecao da reserva, os estados/janelas divergiram entre observadores. Revisar a implementacao antes de atribuir efeitos aos fiscais.",""]
    identity=analysis["nominal_unlimited_identity"]
    if not (identity["same_final_state"] and identity["same_windows"]):
        lines += ["FALHA DE REFERENCIA: o cancelamento ilimitado nao coincidiu com a planta nominal. Revisar esse controle matematico antes de interpretar as ablacoes.",""]
    c=analysis["current"]
    lines += [f"Corrente: maior atuacao matematica nos {c['bounded_cases']} ensaios com teto = {c['maximum_bounded_uA']:.9f} uA.",
              f"Casos que falharam na verificacao do teto algebrico: {', '.join(c['failed_cases']) or 'nenhum'}.",
              "O ensaio unlimited e excluido desse criterio: sua finalidade e retirar deliberadamente a restricao de corrente.",
              "Nenhum desses resultados prova um teto fisico de 90 uA, funcionamento de chips reais ou validade de uma PCB.","",
              "PROTOCOLO ESTATISTICO", "",
              f"Bootstrap pareado: {BOOTSTRAP_REPLICATES} replicas, seed {BOOTSTRAP_SEED}; reamostragem de 500 trajetorias inteiras com reposicao.",
              "As 20 janelas de cada trajetoria ficam juntas. A mesma reamostragem e aplicada aos dois tratamentos.",
              "Intervalos percentis de 2,5% e 97,5%; descrevem sensibilidade as condicoes iniciais deste conjunto, condicionado as mesmas fases e ordem de entradas.",
              "As duas primeiras condicoes iniciais sao prescritas (-0,37 e +0,37); as demais usam a semente registrada. Nao interpretar o intervalo como confiabilidade de hardware.","",
              "COMPARACOES PAREADAS DOS CONJUNTOS DE 10.000", ""]
    for label,pair in analysis["comparisons"].items():
        if "bootstrap" not in pair:
            continue
        ci=pair["bootstrap"]["delta_percentage_points_ci95"]
        lines += [f"{label}: {pair['baseline']} -> {pair['candidate']}",
                  f"  acertos {pair['baseline_correct']} -> {pair['candidate_correct']}/{pair['windows']}; recuperadas={pair['recovered']}; regressoes={pair['regressed']}; saldo={pair['net']:+d}; discordancias={pair['discordant']}; IC95 saldo=[{ci[0]:+.3f},{ci[1]:+.3f}] pp."]
        if label=="healthy_l2_to_common":
            lines.append("  L2 usa atraso/filtro de 5/10 us; comum usa 20/50 us. Este par compara politica e dinamica juntas, como configuracoes completas; nao isola o efeito da regra de alocacao.")
        for code,p in pair["by_input"].items():
            lines.append(f"  entrada {code}: {p['baseline_correct']} -> {p['candidate_correct']}/{p['windows']}; recuperadas={p['recovered']}, regressoes={p['regressed']}, saldo={p['net']:+d}.")
        if "pre_injection_windows_identical" in pair:
            lines.append(f"  Controle de prefixo: {pair['pre_injection_windows']} janelas completas anteriores a injecao, com tabelas identicas={pair['pre_injection_windows_identical']}.")
    lines += ["", "REFINAMENTO DA MALHA LEGADA (2 TRAJETORIAS x 17 JANELAS)", ""]
    for detector,item in analysis["refinement"].items():
        lines.append(f"{detector}: passos {item['steps_us']} us; acertos {item['correct']} de {item['windows_per_step']} em cada passo; alarmes indevidos {item['false_alarms']}.")
        lines.append(f"  Acertos nas tres malhas={item['correct_all_three']}; falhas nas tres={item['failed_all_three']}; classificacoes que mudaram={item['classifications_changed']}.")
        for p in item["successive_pairs"]:
            lines.append(f"  {p['baseline']} -> {p['candidate']}: acertos comuns={p['both_correct']}; discordancias={p['discordant']}; recuperadas={p['recovered']}; novas falhas={p['regressed']}.")
        lines.append(f"  Residuo Y RMS (uA)={item['residual_y_rms_uA']}; D={item['residual_d_rms_uA']}; TV(g)/s={item['g_total_variation_per_s']}.")
    lines += ["", "MATRIZ DE FALHAS (DETECCAO SEPARADA DE RECUPERACAO LOGICA)", ""]
    for item in analysis["fault_matrix"]:
        lines += [f"{item['case']}: detectadas={item['detected']}/{item['injected']}; falsos previos={item['before_fault']}; motivos anteriores carimbados na fronteira={item['pre_fault_reason_at_boundary']}; falsos/saudaveis={item['false_before_or_healthy']}; alarmes tardios={item['late']}; acertos={item['correct_windows']}/{item['total_windows']}.",
                  f"  Latencia desde inicio nominal da falha: {_format_quantiles(item['detection_latency_us'])}.",
                  f"  Latencia desde primeira divergencia de concessao/mensagem invalida: {_format_quantiles(item['latency_from_harm_us'])}; marcador observado em {item['grant_divergence_observed']} trajetorias; alarme anterior ao marcador em {item['alarm_before_grant_divergence']}.",
                  f"  Intervalo entre trip do fiscal e primeira selecao da reserva: {_format_quantiles(item['fallback_after_alarm_us'])}.",
                  f"  Causas registradas: {item['alarm_causes']}; momentos: {item['alarm_timings']}."]
        if item["detector"]=="effective":
            p=analysis["comparisons"][f"fault_{item['fault']}_quota_to_effective"]
            lines.append(f"  Cotas -> efetiva nesta falha: recuperadas={p['recovered']}; novas falhas={p['regressed']}; saldo={p['net']:+d}.")
    lines += ["O nome bruto harm_start e herdado do motor: registra divergencia absoluta de concessao util OU mensagem basica invalida. Uma concessao maior pode beneficiar um canal; esse marcador nao prova dano nem deficit.","", "CANTOS DE TOLERANCIA", ""]
    for item in analysis["corners"]:
        lines.append(f"{item['case']}: alarmes indevidos={item['false_before_or_healthy']}/{item['trajectories']}; acertos={item['correct_windows']}/{item['total_windows']}; causas={item['alarm_causes']}.")
    for label,p in analysis["comparisons"].items():
        if label.startswith("corner_"):
            lines.append(f"  {label}: recuperadas={p['recovered']}; regressoes={p['regressed']}; saldo={p['net']:+d}.")
    lines += ["Os cantos sao ensaios deterministas combinados, nao uma distribuicao de fabricacao.","", "ABLACOES MATEMATICAS", ""]
    for item in analysis["ablations"]:
        lines.append(f"{item['case']}: acertos={item['correct_windows']}/{item['total_windows']}; pico={item['peak_current_uA']:.6f} uA; residuo Y={item['residual_y_rms_uA']:.6f} uA, D={item['residual_d_rms_uA']:.6f} uA; TV(g)/s={item['g_total_variation_per_s']:.6f}.")
    for label,p in analysis["comparisons"].items():
        if label.startswith("ablation_"):
            lines.append(f"  {label}: recuperadas={p['recovered']}; regressoes={p['regressed']}; saldo={p['net']:+d}.")
    identity=analysis["nominal_unlimited_identity"]
    lines += [f"Nominal e cancelamento ilimitado: estados finais identicos={identity['same_final_state']}; tabelas de janelas identicas={identity['same_windows']}.",
              "A identidade testa a referencia algebrica. A ausencia de teto nao constitui uma implementacao utilizavel com 90 uA.",
              "Unlimited cancela as perturbacoes em cada subpasso RK4; ideal calcula a corrente limitada no inicio do passo e a mantem. A diferenca mistura teto/politica com a forma temporal de aplicar a corrente, portanto nao isola o orcamento sozinho.",
              "O controle coordinator/off -> actuator/off a 2,5 us isola a adicao do substituto matematico de atuador nesta matriz, sem provar comportamento de hardware real."]
    ap=analysis["comparisons"]["ablation_coordinator_to_actuator"]
    lines += [f"Incremento do atuador matematico: {ap['baseline_correct']} -> {ap['candidate_correct']}/{ap['windows']}; recuperadas={ap['recovered']}; regressoes={ap['regressed']}; saldo={ap['net']:+d}.","", "TRANSICAO PARA RESERVA COM POLITICA CORRESPONDENTE", ""]
    for detector in ("quota","effective"):
        p=analysis["comparisons"][f"fallback_{detector}"]
        lines.append(f"{detector}, fallback comum -> matched: acertos={p['baseline_correct']} -> {p['candidate_correct']}/{p['windows']}; recuperadas={p['recovered']}; regressoes={p['regressed']}; saldo={p['net']:+d}.")
    lines += ["", "LIMITES E PROVENIENCIA", ""]
    lines.extend(analysis["limitations"])
    lines += ["",f"Core: {analysis['provenance']['core_version']}; SHA256={analysis['provenance']['core_source_sha256']}",
              f"Plano SHA256={analysis['provenance']['plan_sha256']}",
              f"Analisador SHA256={analysis['provenance']['analyzer_sha256']}",
              "Todos os hashes de arquivos/JSONs, configuracoes e auditorias estao em analise.json. Resumos tabulares em resumo.csv; janelas com identificacao do caso em janelas.csv.",
              "Consulte tambem NOTAS_METODOLOGICAS.txt. O RMS agregado do ChaosLab e a raiz da energia media entre trajetorias; a Etapa18 usa media dos RMS individuais. resumo.csv inclui ambos, separados.",
              "Nenhum RAW LTspice removido foi necessario para esta analise; a Etapa18 permanece como referencia de outro modelo e outra malha."]
    return "\n".join(lines)+"\n"


def _csv_bytes(rows: list[dict]) -> bytes:
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def scientific_figures(analysis: dict) -> tuple[bytes, bytes]:
    """Render both scientific formats with the same Matplotlib figure."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Matplotlib e necessario para publicar PNG/SVG; nenhum relatorio alterado") from exc
    matplotlib.rcParams["svg.fonttype"]="none"
    rows={r["case"]:r for r in analysis["rows"]}
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout="constrained")
    fig.suptitle("ChaosLab · Etapa 19 — matemática em passos fixos",fontsize=19)
    labels,names=[],[]
    for fault,label in (("healthy","Sem falha"),("bias","Viés")):
        for detector,dlabel in (("off","desligado"),("quota","cotas"),("effective","efetiva")):
            names.append(f"ensemble_{fault}_{detector}");labels.append(f"{label} · {dlabel}")
    ax=axes[0,0];rates=[rows[name]["correct_percent"] for name in names]
    intervals=np.array([analysis["ensemble_rate_intervals"][name]["candidate_rate_percent_ci95"] for name in names])
    ax.barh(labels,rates,color=["#53687a","#7062a5","#147d92"]*2)
    ax.errorbar(rates,range(len(names)),xerr=np.maximum(0,np.array((rates-intervals[:,0],intervals[:,1]-rates))),fmt="none",color="#18324a",capsize=3)
    ax.set(xlim=(0,100),xlabel="Acertos (%) · IC95 por trajetória",title="A · 10.000 janelas por ensaio, passo 5 µs")
    ax.invert_yaxis()
    ax=axes[0,1]
    pairs=[analysis["comparisons"][f"{fault}_quota_to_effective"] for fault in ("healthy","bias")]
    xx=np.arange(2)
    ax.bar(xx-.18,[p["recovered"] for p in pairs],.36,label="Recuperadas",color="#147d92")
    ax.bar(xx+.18,[p["regressed"] for p in pairs],.36,label="Novas falhas",color="#d27632")
    ax.set(xticks=xx,xticklabels=["Sem falha","Viés +12 µA"],ylabel="Janelas",title="B · Cotas → concessão efetiva");ax.legend()
    ax=axes[1,0]
    for detector,label,color in (("quota","Cotas","#7062a5"),("effective","Efetiva","#147d92")):
        item=analysis["refinement"][detector]
        ax.plot([0,1,2],item["correct"],"o-",label=label,color=color)
    ax.set(xticks=[0,1,2],xticklabels=["5","2,5","1,25"],ylim=(0,34),xlabel="Passo (µs)",ylabel="Acertos em 34",title="C · Refinamento da amostra legada");ax.legend()
    ax=axes[1,1];ax.axis("off")
    lines=["D · Detecção e limites",""]
    for detector,label in (("quota","Cotas"),("effective","Efetiva")):
        faults=[r for r in analysis["fault_matrix"] if r["detector"]==detector]
        corners=[r for r in analysis["corners"] if r["detector"]==detector]
        lines += [f"{label}: detectou {sum(r['detected'] for r in faults)}/{sum(r['injected'] for r in faults)} trajetórias com falha;",
                  f"alarmes nos cantos: {sum(r['false_before_or_healthy'] for r in corners)}/{sum(r['trajectories'] for r in corners)}.",""]
    lines += ["Convergência global não estabelecida.","Teto algébrico de 90 µA; não prova física.","IC95: bootstrap por 500 trajetórias,",f"{BOOTSTRAP_REPLICATES} réplicas, seed {BOOTSTRAP_SEED}."]
    ax.text(0,1,"\n".join(lines),va="top",fontsize=11,color="#18324a",linespacing=1.4)
    for ax in axes.flat:
        if ax.axison:
            ax.grid(axis="y",alpha=.18);ax.set_axisbelow(True)
    png=io.BytesIO();svg=io.BytesIO()
    fig.savefig(png,format="png",dpi=150)
    fig.savefig(svg,format="svg")
    plt.close(fig)
    ET.fromstring(svg.getvalue())
    return png.getvalue(),svg.getvalue()


def publish(analysis: dict, results: dict[str,dict], folder: Path=OUT, *, require_png=False) -> dict:
    """All validations and rendering succeed before any report replacement."""
    report=report_text(analysis)
    png,svg=scientific_figures(analysis)
    windows=[dict(case=name,group=result["group"],**row) for name,result in sorted(results.items()) for row in result["windows"]]
    if len(windows)!=analysis["counts"]["windows"]:
        raise ValueError("Publication refused: not all registered logical windows are present")
    analysis["figures"]=dict(svg="comparacao_etapa19.svg",png="comparacao_etapa19.png" if png is not None else None,
                             png_status="rendered" if png is not None else "matplotlib unavailable; SVG generated")
    payloads={"analise.json":json.dumps(analysis,ensure_ascii=False,allow_nan=False,indent=2).encode("utf-8"),
              "resumo.csv":_csv_bytes(analysis["rows"]),"janelas.csv":_csv_bytes(windows),
              "ETAPA19_RESULTADOS.txt":report.encode("utf-8"),"comparacao_etapa19.svg":svg}
    if png is not None:
        payloads["comparacao_etapa19.png"]=png
    for name,payload in payloads.items():
        _atomic(folder/name,payload)
    return dict(files=list(payloads),cases=analysis["counts"]["cases"],windows=len(windows),png=png is not None)


def self_test() -> dict:
    """Synthetic checks only: no saved experiment is read and no file is written."""
    def example(name, values):
        values=np.array(values,dtype=bool)
        count,windows=values.shape
        cfg=dict(trajectories=count,windows=windows,seed=19,sequence="legacy",dt_us=5.)
        seq=[0,3][:windows]
        rows=[]
        for j in range(count):
            for w in range(windows):
                expected=int(seq[w]==3);good=bool(values[j,w])
                x=1. if (expected==good) else -1.
                rows.append(dict(trajectory=j,window=w,input=seq[w],expected=expected,min=x,max=x,
                                 margin=x if expected else -x,correct=good,window_start_s=w*.05+.03,window_end_s=w*.05+.049))
        per=[dict(trajectory=j,initial_x=float(j),initial_y=-.2) for j in range(count)]
        return dict(name=name,config=cfg,windows=rows,per_trajectory=per)
    a=example("a",[[1,0],[0,1]])
    b=example("b",[[1,1],[1,0]])
    p=paired(a,b)
    assert (p["recovered"],p["regressed"],p["net"],p["both_correct"],p["both_failed"])==(2,1,1,1,0)
    assert p["by_input"]["11"]["net"]==0 and p["by_input"]["00"]["net"]==1
    malformed=json.loads(json.dumps(b));malformed["windows"][0]["window_end_s"]+=1e-6
    try:
        paired(a,malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("Mismatched window boundary accepted")
    base=np.zeros((4,20),dtype=bool)
    all_correct=np.ones((4,20),dtype=bool)
    exact=cluster_bootstrap(base,all_correct,replicates=1000)
    assert exact["delta_percentage_points_ci95"]==[100.,100.]
    grouped=np.repeat([[False],[False],[True],[True]],20,axis=1)
    grouped_ci=cluster_bootstrap(base,grouped,replicates=5000)
    assert grouped_ci["delta_percentage_points_ci95"]==[0.,100.]
    assert grouped_ci==cluster_bootstrap(base,grouped,replicates=5000)
    assert quantiles([None,None])["n"]==0 and quantiles([1,2,3,4])["median"]==2.5
    assert quantiles([-5.,None,10.])["min"]==-5.
    assert _csv_bytes([dict(case="x",correct=True)]).startswith(b"\xef\xbb\xbf")
    return dict(status="passed",synthetic_only=True,checks=["paired recovery/regression counts","matched window identities",
                "known constant bootstrap interval","trajectory-cluster dependence","reproducible bootstrap seed",
                "empty/signed latency quantiles","CSV encoding"],stage19_executed=False,files_written=False)


def synthetic_full_test() -> dict:
    """Exercise every report branch using invented fixtures, never run the ODE."""
    from chaoslab.stage19 import cases
    suite=cases()  # Configuration construction only; no simulator or file calls.
    results={}
    for case in suite:
        cfg=case["config"];n,w=cfg["trajectories"],cfg["windows"]
        seq=np.resize(np.array([0,1,2,3],dtype=int),w).tolist()
        nominal=cfg["profile"] in ("nominal","unlimited")
        offset=0 if nominal else {"off":0,"quota":1,"effective":2}[cfg["detector"]]
        rows=[];correct=np.zeros(n,dtype=int)
        for window in range(w):
            for j in range(n):
                shift=offset+(1 if cfg["fault"]!="healthy" and window>=6 else 0)
                good=(j+2*window+shift)%7!=0
                expected=int(seq[window]==3)
                x=1. if expected==good else -1.
                rows.append(dict(trajectory=j,window=window,input=seq[window],expected=expected,
                    min=x,max=x,margin=x if expected else -x,correct=good,
                    window_start_s=window*.05+.03,window_end_s=window*.05+.049))
                correct[j]+=int(good)
        fault=cfg["fault"]!="healthy"
        detected=fault and cfg["detector"]!="off"
        false=(not fault) and cfg["corner"]!="nominal" and cfg["detector"]=="quota"
        start=0. if cfg["fault"] in ("replay","stale") else 343350.
        per=[]
        for j in range(n):
            per.append(dict(trajectory=j,initial_x=(-.37 if j==0 else .37 if j==1 else j/n*.74-.37),initial_y=-.2,
                final_x=0.,final_y=0.,total_windows=w,correct_windows=int(correct[j]),
                alarm=detected or false,false_alarm=false,detected_fault=detected,alarm_after_fault=False,
                alarm_timing="during_fault" if detected else "healthy" if false else "none",
                alarm_causes=["coherence"] if detected or false else [],fault_injected=fault,
                alarm_time_us=start+70. if detected else 2100. if false else None,
                fallback_time_us=start+75. if detected else 2105. if false else None,
                harm_start_us=start+10. if fault else None,detection_latency_us=70. if detected else None,
                latency_from_harm_us=60. if detected else None,peak_current_uA=133. if cfg["profile"]=="unlimited" else 90.,
                residual_y_rms_uA=float(40+j%3),residual_d_rms_uA=float(20+j%3),g_total_variation_per_s=1000.))
        peak=133. if cfg["profile"]=="unlimited" else 90.
        steps=round(w*.05/(cfg["dt_us"]*1e-6))
        summary=dict(total_windows=n*w,planned_windows=n*w,correct_windows=int(correct.sum()),
            correct_fraction=float(correct.sum()/(n*w)),alarm_trajectories=n*int(detected or false),
            false_alarm_trajectories=n*int(false),detected_fault_trajectories=n*int(detected),
            alarms_after_fault_trajectories=0,fault_trajectories=n*int(fault),peak_current_uA=peak,peak_e_uA=5.,
            residual_y_rms_uA=float(np.sqrt(np.mean([r["residual_y_rms_uA"]**2 for r in per]))),
            residual_d_rms_uA=float(np.sqrt(np.mean([r["residual_d_rms_uA"]**2 for r in per]))),
            g_total_variation_per_s=1000.,reserve_fraction=.25 if detected or false else 0.)
        result=dict(name=case["name"],group=case["group"],status="complete",config=cfg,
            windows=rows,per_trajectory=per,summary=summary,
            timing=dict(steps=steps,planned_steps=steps,simulated_seconds_per_trajectory=steps*cfg["dt_us"]*1e-6,elapsed_s=1.),
            validation=dict(input_sequence=seq,fixed_step=True,physical_hardware_model=False,
                core_version="synthetic",budget_ok=None if cfg["profile"]=="unlimited" else True,
                final_state_sha256="synthetic-nominal" if nominal else case["name"],state_digest=case["name"]))
        audit_result(result,case)
        results[case["name"]]=result
    plan=dict(cases=suite,total_cases=len(suite),planned_windows=sum(r["summary"]["total_windows"] for r in results.values()),limitations=["SYNTHETIC FIXTURE ONLY"])
    provenance=dict(core_version="synthetic",core_source_sha256="not-a-real-source",plan_sha256="synthetic",analyzer_sha256="synthetic")
    analysis=analyze(results,plan,provenance)
    report=report_text(analysis)
    png,svg=scientific_figures(analysis)
    assert len(results)==len(suite) and analysis["counts"]["windows"]==plan["planned_windows"]
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    ET.fromstring(svg)
    assert "SYNTHETIC FIXTURE ONLY" in report
    assert analysis["comparisons"]["fault_impact_quota"]["pre_injection_windows_identical"]
    assert analysis["nominal_unlimited_identity"]["same_windows"]
    assert analysis["current"]["failed_cases"]==[] and len(analysis["current"]["unlimited_exempt_cases"])==1
    assert any(abs(r["residual_y_rms_uA"]-r["mean_trajectory_residual_y_rms_uA"])>1e-5 for r in analysis["rows"])
    broken=json.loads(json.dumps(results[suite[0]["name"]]))
    broken["windows"][0]["correct"]=not broken["windows"][0]["correct"]
    try:
        audit_result(broken,suite[0])
    except ValueError:
        pass
    else:
        raise AssertionError("Tampered logical criterion accepted")
    return dict(status="passed",synthetic_only=True,cases=len(suite),windows=plan["planned_windows"],
                report_characters=len(report),png_bytes=len(png),svg_bytes=len(svg),
                checks=["all synthetic case audits","all paired comparison/report branches","dynamic plan counts",
                        "pre-injection causal prefix","unlimited budget exemption","two RMS aggregation definitions",
                        "strict logical-tamper rejection","Matplotlib PNG/SVG rendering"],
                stage19_executed=False,research_outputs_written=False)


def main():
    parser=argparse.ArgumentParser(description="Auditar e relatar todos os ensaios registrados da Etapa 19")
    parser.add_argument("--self-test",action="store_true",help="Somente testes sinteticos; nao le/escreve resultados")
    parser.add_argument("--self-test-full",action="store_true",help="Relatorio/figuras com fixtures sinteticas completas, sem executar a simulacao")
    parser.add_argument("--require-png",action="store_true",help="Exigir matplotlib e PNG antes de publicar qualquer arquivo")
    args=parser.parse_args()
    if args.self_test or args.self_test_full:
        checked=self_test()
        if args.self_test_full:
            checked["full"]=synthetic_full_test()
        print(json.dumps(checked,ensure_ascii=False,indent=2))
        return
    plan,results,provenance=load_complete_suite()
    analysis=analyze(results,plan,provenance)
    print(json.dumps(publish(analysis,results,require_png=args.require_png),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
