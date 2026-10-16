r"""Opt-in Streamlit checks; not part of automatic scientific test discovery.

From the Violeta directory, in a normal PowerShell terminal::

    .venv\Scripts\python.exe -m chaoslab.test_dashboard
    .venv\Scripts\python.exe -m chaoslab.test_dashboard --worker-smoke

The default only reads the dashboard and existing research. ``--worker-smoke``
additionally runs 2 trajectories x 1 logical window at h=5 us, using the actual
background worker and a mocked save_result: no scientific result is saved.
It refuses to start while the external Stage 19 batch is active. The wrapper
has its own AppTest session and does not change app.py or control the CLI batch.

AppTest needs a local asyncio socket pair. Run outside a sandbox that blocks
local sockets; that restriction can block AppTest before its timeout begins.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

APP = ROOT / "chaoslab" / "app.py"
STAGE18 = ROOT / "experiments" / "ltspice-caos" / "etapa18"
STAGE19 = ROOT / "experiments" / "ltspice-caos" / "etapa19"


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def batch_running() -> bool:
    return read_json(STAGE19 / "progresso.json", {}).get("status") == "running"


def no_exceptions(app: AppTest) -> None:
    assert not app.exception, "\n".join(str(item.value) for item in app.exception)


def displayed_int(text: str) -> int:
    return int(str(text).replace(".", "").replace(" ", ""))


def readonly_checks(timeout: int) -> dict:
    before_running = batch_running()
    report = read_json(STAGE19 / "analise.json", {})
    report_ready = report.get("status") in ("complete", "completed") and (STAGE19 / "ETAPA19_RESULTADOS.txt").exists()
    known_names = {item.get("name") for path in (STAGE19 / "completed").glob("*.json")
                   if (item := read_json(path, {})).get("name") and Path(item.get("path", "")).is_file()}
    app = AppTest.from_file(str(APP), default_timeout=timeout).run()
    no_exceptions(app)
    assert [tab.label for tab in app.tabs] == ["Laboratório", "Resultados", "Referência · Etapa 18", "Armazenamento", "Ferramentas"]
    metrics = {item.label: item.value for item in app.metric}
    checks = ["five tabs", "no render exceptions"]

    for label in ("Espaço livre no disco", "Pasta da pesquisa", "Resultados do ChaosLab"):
        assert label in metrics and "—" not in metrics[label], f"Storage metric missing: {label}"
    checks.append("storage cards")

    trajectories = read_json(STAGE18 / "trajetorias.json")
    summaries = read_json(STAGE18 / "resumo.json")
    assert isinstance(trajectories, list) and isinstance(summaries, list), "Stage 18 sources are required"
    table = next(frame.value for frame in app.dataframe
                 if {"Sinais indevidos · cotas", "Alarmes indevidos · topo"}.issubset(frame.value.columns))
    for source in summaries:
        name = source["arquivo"]
        row = table.loc[table["Ensaio"] == name].iloc[0]
        expected_quota = sum(bool(item.get("cota_alarme_indevido")) for item in trajectories if item["arquivo"] == name)
        assert int(row["Sinais indevidos · cotas"]) == expected_quota, name
        assert int(row["Alarmes indevidos · topo"]) == int(source["alarmes_indevidos"]), name
    expected_v2 = sum(bool(item.get("cota_alarme_indevido")) for item in trajectories if item["arquivo"] == "L2_5_10_v2")
    assert displayed_int(metrics["Sinais indevidos · fiscal de cotas"]) == expected_v2
    checks.append("Stage 18 quota/top alarms independently sourced")

    if before_running and batch_running():
        assert next(button for button in app.button if button.label == "Ensaio em execução").disabled
        checks.append("external batch blocks new UI workers")
    if known_names:
        labels = next(item.options for item in app.selectbox if item.label == "Abrir execução")
        assert known_names.issubset(set(labels)), "Research identifiers missing from saved-run selector"
        checks.append("readable research identifiers")
    for element in app.dataframe:
        frame = element.value
        if {"Ensaio", "Corretas", "Pico (µA)"}.issubset(frame.columns):
            assert "summary" not in frame.columns
            assert not any(isinstance(value, dict) for value in frame.to_numpy().ravel())
            checks.append("flat completed-case table")
            break
    if report_ready:
        counts = report["counts"]
        for label, field in [("Ensaios concluídos", "cases"), ("Trajetórias avaliadas", "trajectories"),
                             ("Janelas avaliadas", "windows"), ("Ensaios de 10.000 janelas", "ensemble_cases")]:
            assert displayed_int(metrics[label]) == counts[field], field
        keys = {element.key for element in app.get("download_button")}
        assert {"download_stage19_report", "download_stage19_analysis"}.issubset(keys)
        checks.append("published Stage 19 report cards and downloads")
    return dict(mode="readonly", status="passed", checks=checks, report_available=report_ready)


def worker_smoke(timeout: int) -> dict:
    if batch_running():
        raise RuntimeError("Stage 19 está em execução. Aguarde o lote terminar antes de usar --worker-smoke.")
    # run_name avoids main(): the wrapper uses only a separate UI worker/session.
    wrapper = f"""
import runpy
import streamlit as st
ns = runpy.run_path({str(APP)!r}, run_name='chaoslab_dashboard_smoke')
if ns['external_batch']().get('status') == 'running':
    st.error('Stage 19 active: smoke worker refused.')
    st.stop()
if 'chaoslab_job' not in st.session_state:
    config = ns['Config'](dt_us=5.0, trajectories=2, windows=1,
                          profile='coordinator', trace_points=200, monitor_every=1000)
    st.session_state['chaoslab_job'] = ns['new_job'](config)
ns['live_panel']()
"""
    with patch("chaoslab.storage.save_result", return_value="UI-smoke-memory-only") as save:
        app = AppTest.from_string(wrapper, default_timeout=timeout).run()
        no_exceptions(app)
        assert "chaoslab_job" in app.session_state, "Smoke worker refused because a batch became active"
        job = app.session_state["chaoslab_job"]
        try:
            job["thread"].join(timeout=timeout)
            assert not job["thread"].is_alive(), "UI smoke worker exceeded timeout"
            app.run()
            no_exceptions(app)
            assert job["state"] == "done", job.get("error")
            assert job["result"]["summary"]["total_windows"] == 2
            assert job["result"]["status"] in ("complete", "completed")
            assert len(app.get("plotly_chart")) >= 3
            assert save.call_count == 1 and job["saved"] == "UI-smoke-memory-only"
        finally:
            if job["thread"].is_alive():
                job["cancel"].set()  # Only the worker created by this test.
                job["thread"].join(timeout=10)
    return dict(mode="worker-smoke", status="passed", trajectories=2, windows=2,
                dt_us=5.0, scientific_results_saved=0,
                checks=["actual background worker", "completion", "plots and window map", "mocked persistence"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--worker-smoke", action="store_true", help="Also run two logical windows in memory, only while Stage 19 is idle.")
    parser.add_argument("--timeout", type=int, default=90, help="AppTest/worker timeout in seconds (default: 90).")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    outputs = [readonly_checks(args.timeout)]
    if args.worker_smoke:
        outputs.append(worker_smoke(args.timeout))
    print(json.dumps(dict(status="passed", tests=outputs), indent=2))


if __name__ == "__main__":
    main()
