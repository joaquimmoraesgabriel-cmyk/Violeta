"""Registered Stage 19 suite, compact resumable outputs and live progress."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from chaoslab.core import Config, run, CORE_VERSION
from chaoslab.storage import ROOT, save_result, load_result, _atomic

OUT = ROOT / "experiments" / "ltspice-caos" / "etapa19"


def write_json(path, data):
    _atomic(Path(path), json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8"))


def cases():
    suite = []

    def add(name, group, **kw):
        defaults = dict(dt_us=5., trajectories=2, windows=17, seed=19019,
                        policy="l2", detector="effective", fallback=True,
                        fault="healthy", profile="actuator", sequence="legacy",
                        trace_points=1200, monitor_every=2000)
        defaults.update(kw)
        config = Config(**defaults)
        config.validate()
        suite.append(dict(name=name, group=group, config=asdict(config)))

    # Paired initial states and a shared balanced input sequence; 500 x 20 = 10000.
    for fault in ("healthy", "bias"):
        for detector in ("off", "quota", "effective"):
            add(f"ensemble_{fault}_{detector}", "ensemble_10000", fault=fault,
                detector=detector, trajectories=500, windows=20, sequence="balanced")
    add("ensemble_healthy_common", "ensemble_10000", detector="off", policy="common",
        trajectories=500, windows=20, sequence="balanced")
    # Refinement does not assume long chaotic trajectories should coincide.
    for detector in ("quota", "effective"):
        for dt in (5., 2.5, 1.25):
            add(f"refine_{detector}_{dt:g}", "refinement", detector=detector, dt_us=dt)
    for profile in ("nominal", "unlimited", "ideal", "sensors", "coordinator", "actuator"):
        add(f"ablation_{profile}", "ablation", profile=profile, detector="off", dt_us=2.5)
    for fault in ("bias", "replay", "stale", "dropout", "double", "starve"):
        for detector in ("quota", "effective"):
            add(f"fault_{fault}_{detector}", "fault_matrix", fault=fault,
                detector=detector, dt_us=2.5)
    for policy in ("common", "l2"):
        for corner in ("plus", "minus"):
            for detector in ("quota", "effective"):
                add(f"corner_{policy}_{corner}_{detector}", "corners", policy=policy,
                    corner=corner, detector=detector, dt_us=2.5)
    for detector in ("quota", "effective"):
        add(f"matched_bias_{detector}", "fallback", fault="bias", detector=detector,
            fallback_policy="matched", dt_us=2.5)
    return suite


def signature(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()


def execute(case):
    status_path = OUT / "progress_cases" / (case["name"] + ".json")
    last = 0.

    def progress(snapshot):
        nonlocal last
        now = time.monotonic()
        if now-last < 3 and snapshot.get("fraction", 0) < 1:
            return
        last = now
        # Live curves are bounded to 200 samples by the engine.
        try:
            write_json(status_path, dict(case=case["name"], **snapshot))
        except OSError as exc:
            # Telemetry failure must not discard a mathematical trajectory.
            print(json.dumps({"progress_warning":case["name"],"error":str(exc)}),flush=True)

    result = run(Config(**case["config"]), progress=progress)
    result["name"] = case["name"]
    result["group"] = case["group"]
    result["suite_signature"] = signature(case)
    result["core_source_sha256"] = hashlib.sha256((ROOT/"chaoslab"/"core.py").read_bytes()).hexdigest()
    target = save_result(result)
    record = dict(name=case["name"], group=case["group"], path=target,
                  config=result["config"], summary=result["summary"], timing=result["timing"],
                  validation=result["validation"], signature=signature(case))
    write_json(OUT / "completed" / (case["name"] + ".json"), record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--only", nargs="*", help="Names for a selective rerun, all by default")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "progress_cases").mkdir(exist_ok=True)
    (OUT / "completed").mkdir(exist_ok=True)
    suite = cases()
    source_hash = hashlib.sha256((ROOT/"chaoslab"/"core.py").read_bytes()).hexdigest()
    registration = dict(schema="chaoslab-stage19-v1", core_version=CORE_VERSION,
        core_source_sha256=source_hash, python=sys.version, numpy=np.__version__, platform=platform.platform(),
        total_cases=len(suite), planned_windows=sum(c["config"]["trajectories"]*c["config"]["windows"] for c in suite),
        stage18_sources={name:hashlib.sha256((OUT.parent/"etapa18"/name).read_bytes()).hexdigest()
                         for name in ("MLC_cotas_v2.inc","resumo.json","trajetorias.json","verificacao_entrega.json")},
        hypotheses=["Useful grants reduce alarms caused solely by unused capacity redistribution.",
                    "Raw protocol guards retain invalid-message detection.",
                    "Detection need not improve logical recovery; report recovered AND regressed windows.",
                    "Passive observers must leave the same fixed-grid plant trajectory bitwise unchanged.",
                    "Coarse ensemble rates are exploratory until refinement is stable."],
        limitations=["Each 10000-window ensemble is 500 independent initializations x20 consecutive windows, not a500s single path.",
                     "All paths share forcing phases and input order; uncertainty estimates describe initial-condition sensitivity only.",
                     "Fixed-grid extrema can miss between-grid crossings. RK4 plant plus ZOH splitting is not globally fourth order.",
                     "No physical op-amp/PCB model, nor Stage18 top-command fault detector, is implemented here."],
        cases=suite)
    registry_path = OUT / "plano_registrado.json"
    if registry_path.exists() and list((OUT/"completed").glob("*.json")):
        previous = json.loads(registry_path.read_text(encoding="utf-8"))
        if previous["core_source_sha256"] != source_hash:
            raise RuntimeError("Core mudou após o início do lote; use nova revisão/arquivo de resultados.")
    write_json(registry_path, registration)
    if args.prepare:
        print(json.dumps({"prepared":str(registry_path),"cases":len(suite),"windows":registration["planned_windows"]}))
        return
    selected = [c for c in suite if not args.only or c["name"] in args.only]
    if not selected:
        raise ValueError("Nenhum caso selecionado")
    completed = []
    failed = []
    pending = []
    for case in selected:
        done = OUT/"completed"/(case["name"]+".json")
        if done.exists():
            record = json.loads(done.read_text(encoding="utf-8"))
            if record.get("signature") == signature(case) and Path(record["path"]).exists():
                completed.append(record)
                continue
        pending.append(case)
        write_json(OUT/"progress_cases"/(case["name"]+".json"),
                   dict(case=case["name"],status="queued",fraction=0.,steps=0))
    started = time.monotonic()

    def update(status, futures=None):
        active = []
        for case in (futures or {}).values():
            p = OUT/"progress_cases"/(case["name"]+".json")
            if p.exists():
                try:
                    snap = json.loads(p.read_text(encoding="utf-8"))
                    if snap.get("status") == "running":
                        active.append(snap)
                except (OSError,ValueError):
                    pass
        total_steps = sum(math_steps(c["config"]) for c in selected)
        finished_steps = sum(r["timing"]["steps"] for r in completed)
        fraction = (finished_steps+sum(s.get("steps",0) for s in active))/max(1,total_steps)
        record = dict(status=status, case=", ".join(s["case"] for s in active),
            case_index=len(completed), total_cases=len(selected), fraction=min(1.,fraction),
            elapsed_s=time.monotonic()-started, active=active,
            trace=active[0].get("trace",{}) if active else {},
            completed_windows=sum(r["summary"]["total_windows"] for r in completed)+sum(s.get("completed_windows",0) for s in active),
            correct_windows=sum(r["summary"]["correct_windows"] for r in completed)+sum(s.get("correct_windows",0) for s in active),
            peak_budget_uA=max([r["summary"]["peak_current_uA"] for r in completed]+[s.get("peak_budget_uA",0) for s in active]+[0]),
            cases_completed=[dict(name=r["name"],summary=r["summary"]) for r in completed])
        try:
            write_json(OUT/"progresso.json", record)
        except OSError as exc:
            print(json.dumps({"monitor_warning":str(exc)}),flush=True)
    update("running")
    try:
        with ProcessPoolExecutor(max_workers=min(3,max(1,args.workers))) as pool:
            futures = {pool.submit(execute,c):c for c in pending}
            while futures:
                ready,_ = wait(futures, timeout=3, return_when=FIRST_COMPLETED)
                for future in ready:
                    case = futures.pop(future)
                    try:
                        result = future.result()
                    except Exception as exc:
                        failure = dict(case=case["name"],type=type(exc).__name__,error=str(exc))
                        failed.append(failure)
                        write_json(OUT/"falhas_execucao.json",failed)
                        print(json.dumps(failure),flush=True)
                        continue
                    completed.append(result)
                    print(json.dumps(dict(done=case["name"],n=len(completed),total=len(selected),
                        correct=result["summary"]["correct_windows"],windows=result["summary"]["total_windows"],
                        seconds=result["timing"]["elapsed_s"])),flush=True)
                update("running",futures)
        if failed:
            update("failed")
            raise RuntimeError("Casos interrompidos registrados; execute novamente para retomá-los.")
        write_json(OUT/"resultados.json", sorted(completed,key=lambda r:r["name"]))
        update("completed")
    except BaseException as exc:
        update("failed")
        write_json(OUT/"falha_lote.json",dict(type=type(exc).__name__,error=str(exc)))
        raise


def math_steps(config):
    return round(config["windows"]*.05/(config["dt_us"]*1e-6))


if __name__ == "__main__":
    main()
