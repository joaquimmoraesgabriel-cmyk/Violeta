"""ChaosLab: visual, local control panel for the fixed-step research engine.

Run from the repository root with ``python -m streamlit run chaoslab/app.py``.
The worker never calls Streamlit; observers only read bounded snapshots.
"""

from __future__ import annotations

import copy
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
STAGE19 = ROOT / "experiments" / "ltspice-caos" / "etapa19"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chaoslab.core import Config, run
from chaoslab.storage import disk_status, list_runs, load_result, save_result


st.set_page_config(
    page_title="ChaosLab · Violeta",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

TEAL = "#087f8c"
INDIGO = "#5149b9"
ORANGE = "#e68932"
RED = "#d25164"
INK = "#142a43"
MUTED = "#65778d"

st.markdown(
    """
    <style>
    html, body, [class*="css"], [data-testid="stApp"] {font-family: 'Segoe UI', sans-serif;}
    [data-testid="stAppViewContainer"] {background: #f5f7fb;}
    [data-testid="stHeader"] {background: rgba(245,247,251,.92);}
    [data-testid="stSidebar"] {background: #edf1f7; border-right:1px solid #dce3ed;}
    .block-container {padding-top:2.4rem; padding-bottom:3rem; max-width:1600px;}
    h1, h2, h3 {color:#142a43; letter-spacing:-.035em;}
    h1 {font-weight:700 !important;}
    [data-testid="stMetric"] {background:white; border:1px solid #e0e6ee;
      border-radius:14px; padding:17px 19px; box-shadow:0 2px 4px #142a4303;}
    [data-testid="stMetricLabel"] {color:#65778d;}
    [data-testid="stMetricValue"] {color:#142a43; font-size:1.8rem;}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {gap:24px; border-bottom:1px solid #dce3ed;}
    [data-testid="stTabs"] [data-baseweb="tab"] {font-weight:600; padding-bottom:14px;}
    div.stButton > button[kind="primary"] {background:#087f8c; border-color:#087f8c;}
    .lab-eyebrow {font-size:12px;letter-spacing:.18em;font-weight:700;color:#087f8c;margin-bottom:8px;}
    .lab-subtitle {color:#65778d;font-size:16px;max-width:780px;margin-bottom:22px;line-height:1.6;}
    .lab-pill {display:inline-block;border:1px solid #cbdde4;border-radius:20px;
      padding:5px 12px;color:#28526c;background:#eff8fa;font-size:12px;margin:0 6px 9px 0;}
    .lab-note {background:#e8f4f3;border-left:3px solid #087f8c;padding:14px 18px;
      border-radius:0 10px 10px 0;color:#315467;line-height:1.6;}
    .lab-empty {padding:42px 32px;border:1px dashed #bfcdda;background:#f9fbfd;
      border-radius:18px;text-align:center;color:#65778d;}
    .lab-empty strong {font-size:22px;color:#142a43;display:block;margin:9px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def number(value: Any, digits: int = 0) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(value):
        return "—"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def elapsed(seconds: Any) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "—"
    return f"{seconds // 60:d} min {seconds % 60:02d} s" if seconds >= 60 else f"{seconds} s"


def choose(data: dict, *keys: str, default=None):
    return next((data[key] for key in keys if key in data and data[key] is not None), default)


def chart_style(figure: go.Figure, height: int = 370) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=15, r=15, t=38, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Segoe UI, sans-serif", color=INK, size=12),
        legend=dict(orientation="h", y=1.12, x=0),
        hovermode="x unified",
    )
    figure.update_xaxes(gridcolor="#e9eef5", zerolinecolor="#bcc9d8")
    figure.update_yaxes(gridcolor="#e9eef5", zerolinecolor="#bcc9d8")
    return figure


def render_trace(trace: dict, key: str, compact: bool = False, budget_uA: float = 90.) -> None:
    t = trace.get("t_s", [])
    if len(t) < 2:
        st.caption("O traçado aparece assim que o primeiro bloco de cálculo estiver pronto.")
        return
    time_ms = np.asarray(t, dtype=float) * 1000
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)
    for field, label, color in [("x", "Estado X", TEAL), ("y", "Estado Y", INDIGO)]:
        values = trace.get(field, [])
        if len(values) == len(t):
            fig.add_trace(go.Scatter(x=time_ms, y=values, name=label, line=dict(color=color, width=1.5)), row=1, col=1)
    for field, label, color in [
        ("current_y_uA", "Atuador Y", TEAL),
        ("current_d_uA", "Pilar D", INDIGO),
        ("current_e_uA", "Reserva E", ORANGE),
    ]:
        values = trace.get(field, [])
        if len(values) == len(t):
            fig.add_trace(go.Scatter(x=time_ms, y=values, name=label, line=dict(color=color, width=1.2)), row=2, col=1)
    fig.update_yaxes(title_text="Estado", row=1, col=1)
    fig.update_yaxes(title_text="Corrente (µA)", row=2, col=1)
    fig.update_xaxes(title_text="Tempo da trajetória (ms)", row=2, col=1)
    st.plotly_chart(chart_style(fig, 430 if compact else 510), width="stretch", key=f"{key}_trace")
    st.caption("Trajetória representativa, amostrada para visualização. Os extremos e as janelas são avaliados em todos os passos.")
    if not compact:
        with st.expander("Inspecionar orçamento e fiscal"):
            allocation = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.15)
            for field, label, color, row in [
                ("request_y_uA", "|Pedido Y|", TEAL, 1),
                ("quota_y_uA", "Cota Y", INDIGO, 1),
                ("grant_y_uA", "|Concessão Y|", ORANGE, 1),
                ("budget_uA", "Soma de correntes", TEAL, 2),
                ("error_uA", "Discrepância do fiscal", RED, 2),
            ]:
                values = trace.get(field, [])
                if len(values) == len(t):
                    allocation.add_trace(go.Scatter(x=time_ms, y=np.abs(values), name=label, line=dict(color=color, width=1.3)), row=row, col=1)
            allocation.add_hline(y=budget_uA, line_dash="dot", line_color=MUTED, annotation_text=f"Orçamento · {budget_uA:g} µA", row=2, col=1)
            allocation.add_hline(y=6.5, line_dash="dot", line_color=RED, annotation_text="Discrepância · 6,5 µA", row=2, col=1)
            allocation.update_yaxes(title="µA")
            allocation.update_xaxes(title="Tempo (ms)", row=2, col=1)
            st.plotly_chart(chart_style(allocation, 460), width="stretch", key=f"{key}_allocation")


def render_summary(summary: dict, key: str) -> None:
    total = choose(summary, "total_windows", "completed_windows", default=0)
    correct = choose(summary, "correct_windows", default=0)
    cols = st.columns(4)
    cols[0].metric("Janelas corretas", f"{number(correct)} / {number(total)}")
    cols[1].metric("Recuperação lógica", f"{number(100 * correct / total, 1)}%" if total else "—")
    cols[2].metric("Pico de atuação", f"{number(choose(summary, 'peak_current_uA', 'peak_budget_uA'), 3)} µA")
    cols[3].metric("Trajetórias com alarme", number(choose(summary, "alarm_trajectories", "alarms")))
    with st.expander("Resíduos, falhas e estresse dinâmico", expanded=False):
        cols = st.columns(3)
        cols[0].metric("Resíduo RMS · Y", f"{number(summary.get('residual_y_rms_uA'), 3)} µA")
        cols[1].metric("Resíduo RMS · D", f"{number(summary.get('residual_d_rms_uA'), 3)} µA")
        cols[2].metric("Variação total de g(x) / s", number(summary.get("g_total_variation_per_s"), 2))
        st.write(
            f"Alarmes em trajetórias saudáveis: **{number(summary.get('false_alarm_trajectories'))}** · "
            f"Trajetórias com falha detectada: **{number(summary.get('detected_fault_trajectories'))} / "
            f"{number(summary.get('fault_trajectories'))}**."
        )


def render_windows(result: dict, key: str) -> None:
    rows = result.get("windows", [])
    if not rows:
        return
    frame = pd.DataFrame(rows)
    tid = next((name for name in ("trajectory", "trajetoria", "trajectory_id") if name in frame), None)
    wid = next((name for name in ("window", "janela", "window_index") if name in frame), None)
    if tid and wid and "correct" in frame:
        matrix = frame.pivot_table(index=tid, columns=wid, values="correct", aggfunc="first")
        if matrix.shape[0] > 100:
            st.caption("Mapa das primeiras 100 trajetórias. A tabela exportada contém todas as janelas.")
            matrix = matrix.iloc[:100]
        if matrix.shape[1] > 120:
            st.caption("Mapa limitado às primeiras 120 janelas por trajetória; o resumo usa a execução completa.")
            matrix = matrix.iloc[:, :120]
        fig = go.Figure(go.Heatmap(
            z=matrix.to_numpy(dtype=float), x=matrix.columns, y=matrix.index,
            zmin=0, zmax=1, colorscale=[[0, "#e8a29f"], [0.499, "#e8a29f"], [0.5, "#37a89c"], [1, "#37a89c"]],
            showscale=False,
            hovertemplate="Trajetória %{y}<br>Janela %{x}<br>Correta: %{z}<extra></extra>",
        ))
        fig.update_xaxes(title="Janela lógica")
        fig.update_yaxes(title="Trajetória", autorange="reversed")
        st.plotly_chart(chart_style(fig, min(470, max(230, 150 + 8 * len(matrix)))), width="stretch", key=f"{key}_windows")
        st.caption("Verde: sinal correto durante toda a janela de avaliação. Coral: ao menos uma violação.")
    with st.expander("Tabela das janelas e exportação"):
        st.dataframe(frame.head(1000), width="stretch", hide_index=True)
        if len(frame) > 1000:
            st.caption("Prévia de 1.000 linhas. O arquivo CSV inclui o conjunto completo.")
        st.download_button("Baixar métricas das janelas · CSV", frame.to_csv(index=False).encode("utf-8-sig"), file_name="chaoslab_janelas.csv", mime="text/csv", key=f"{key}_csv")


def new_job(config: Config) -> dict:
    job = {
        "lock": threading.Lock(), "cancel": threading.Event(), "state": "running",
        "snapshot": {"fraction": 0.0, "completed_windows": 0, "elapsed_s": 0.0},
        "result": None, "error": None, "saved": None, "started": time.monotonic(),
    }

    def progress(snapshot):
        with job["lock"]:
            job["snapshot"] = copy.deepcopy(snapshot)

    def worker():
        try:
            result = run(config, progress=progress, cancelled=job["cancel"].is_set)
            cancelled = job["cancel"].is_set()
            saved = None
            save_error = None
            if not cancelled:
                try:
                    saved = str(save_result(result))
                except Exception as exc:
                    save_error = str(exc)
            with job["lock"]:
                job.update(result=result, state="cancelled" if cancelled else "done", saved=saved, save_error=save_error)
        except Exception as exc:
            with job["lock"]:
                job.update(state="error", error=f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=worker, name="chaoslab-ui-worker", daemon=True)
    job["thread"] = thread
    thread.start()
    return job


def snapshot_job(job: dict) -> dict:
    with job["lock"]:
        return {name: copy.deepcopy(job.get(name)) for name in ("state", "snapshot", "result", "error", "saved", "save_error")}


def external_batch() -> dict:
    path = STAGE19 / "progresso.json"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


@st.fragment(run_every="1s")
def batch_panel():
    batch = external_batch()
    if not batch:
        return
    state = batch.get("status")
    previous = st.session_state.get("chaoslab_external_state")
    st.session_state["chaoslab_external_state"] = state
    if previous != state:
        st.rerun()
    running = state == "running"
    st.markdown("#### " + ("● Lote da Etapa 19 em andamento" if running else "Lote da Etapa 19"))
    case_index = batch.get("case_index", 0)
    total_cases = batch.get("total_cases", 0)
    st.caption(f"{number(case_index)} de {number(total_cases)} ensaios concluídos · {elapsed(batch.get('elapsed_s'))}")
    fraction = float(batch.get("fraction", 0.0))
    st.progress(min(1.0, max(0.0, fraction)), text=f"Progresso do lote: {number(fraction * 100, 1)}%")
    cols = st.columns(3)
    cols[0].metric("Janelas concluídas no lote", number(batch.get("completed_windows", 0)))
    cols[1].metric("Janelas corretas no lote", number(batch.get("correct_windows", 0)))
    cols[2].metric("Pico no lote · inclui ablações", f"{number(batch.get('peak_budget_uA'), 3)} µA")
    if running:
        st.info("O lote usa o motor local. Novos ensaios pela interface ficam disponíveis quando ele terminar.")
        if batch.get("case"):
            st.caption(f"Em execução: {batch['case']}")
        if batch.get("trace"):
            if batch.get("active"):
                st.caption(f"Traçado ao vivo: {batch['active'][0].get('case', 'ensaio ativo')}")
            render_trace(batch["trace"], "external_batch", compact=True)
    elif state in ("completed", "complete", "done"):
        st.success("Lote concluído. Consulte as execuções e comparações na aba Resultados.")
    elif state in ("error", "failed"):
        st.error(f"O lote parou: {batch.get('error', 'Consulte o registro da execução.')} Os ensaios concluídos permanecem salvos.")
    completed = batch.get("cases_completed", [])
    if completed:
        with st.expander(f"Ensaios concluídos · {len(completed)}", expanded=not running):
            rows = []
            for item in completed:
                summary = item.get("summary", item)
                rows.append({
                    "Ensaio": item.get("name", "—"),
                    "Corretas": summary.get("correct_windows"),
                    "Janelas": summary.get("total_windows"),
                    "Alarmes indevidos": summary.get("false_alarm_trajectories"),
                    "Pico (µA)": choose(summary, "peak_current_uA", "peak_budget_uA"),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.divider()


@st.fragment(run_every="1s" if st.session_state.get("chaoslab_job", {}).get("state") == "running" else None)
def live_panel():
    job = st.session_state.get("chaoslab_job")
    if not job:
        if external_batch().get("status") == "running":
            return
        st.markdown('<div class="lab-empty">◈<strong>O laboratório está pronto.</strong>Escolha o ensaio na lateral e inicie uma execução.<br>Os gráficos e as métricas aparecerão aqui durante o cálculo.</div>', unsafe_allow_html=True)
        return
    view = snapshot_job(job)
    state = view["state"]
    previous = st.session_state.get("chaoslab_last_state")
    st.session_state["chaoslab_last_state"] = state
    if previous == "running" and state != "running":
        st.rerun()
    snap = view["snapshot"] or {}
    if state == "running":
        left, right = st.columns([5, 1])
        left.markdown("**● Calculando em passos fixos**")
        if right.button("Interromper", width="stretch", key="stop_simulation"):
            job["cancel"].set()
            st.toast("Interrupção solicitada. O bloco atual será encerrado.")
        fraction = float(snap.get("fraction", 0.0))
        st.progress(min(1.0, max(0.0, fraction)), text=f"{number(fraction * 100, 1)}% · {number(snap.get('completed_windows', 0))} janelas concluídas · {elapsed(time.monotonic() - job['started'])}")
        cols = st.columns(3)
        cols[0].metric("Janelas corretas até agora", number(snap.get("correct_windows", 0)))
        cols[1].metric("Pico de atuação até agora", f"{number(snap.get('peak_budget_uA'), 3)} µA")
        cols[2].metric("Passos do integrador", "Fixos")
        render_trace(snap.get("trace", {}), "live", compact=True)
    elif state == "error":
        st.error("A execução foi interrompida por um erro. Os resultados anteriores continuam disponíveis.")
        st.code(view["error"], language=None)
    else:
        result = view["result"] or {}
        if state == "cancelled":
            st.warning("Execução interrompida. Os dados parciais permanecem nesta sessão e não foram salvos como um ensaio concluído.")
        else:
            st.success("Execução concluída. Resultados compactos salvos." if view.get("saved") else "Cálculo concluído. Resultado disponível em memória.")
        if view.get("save_error"):
            st.warning(f"Não foi possível salvar: {view['save_error']}")
        render_summary(result.get("summary", {}), "live_done")
        render_trace(result.get("trace", {}), "live_done")
        render_windows(result, "live_done")
        if state == "done":
            with st.expander("Reprodutibilidade e validação"):
                st.json({"config": result.get("config"), "timing": result.get("timing"), "validation": result.get("validation"), "arquivo": view.get("saved")})


def sidebar() -> Config | None:
    with st.sidebar:
        st.markdown("### ◈ ChaosLab")
        st.caption("VIOLETA · LABORATÓRIO LOCAL")
        st.divider()
        active = any(st.session_state.get(k, {}).get("state") == "running" for k in
                     ("chaoslab_job", "tools_job", "tools_replay")) or external_batch().get("status") == "running"
        preset = st.selectbox("Tamanho do ensaio", ["Explorar · 136 janelas", "Pesquisa · 10.000 janelas", "Ponte com a Etapa 18", "Personalizado"], disabled=active)
        if preset == "Explorar · 136 janelas":
            trajectories, windows, sequence = 8, 17, "balanced"
        elif preset == "Pesquisa · 10.000 janelas":
            trajectories, windows, sequence = 500, 20, "balanced"
        elif preset == "Ponte com a Etapa 18":
            trajectories, windows, sequence = 4, 17, "legacy"
        else:
            trajectories = int(st.number_input("Trajetórias em paralelo", 1, 10000, 20, disabled=active))
            windows = int(st.number_input("Janelas por trajetória", 1, 10000, 20, disabled=active))
            sequence = st.selectbox("Sequência de entradas", ["balanced", "legacy"], format_func=lambda x: "Balanceada e reprodutível" if x == "balanced" else "Sequência da Etapa 18", disabled=active)
        total = trajectories * windows
        st.caption(f"{number(trajectories)} trajetórias × {number(windows)} janelas = **{number(total)} janelas lógicas**. Cada janela ocupa 50 ms.")
        dt_us = float(st.selectbox("Passo fixo (µs)", [5.0, 2.5, 1.25], disabled=active))
        policy = st.selectbox("Coordenador", ["l2", "common"], format_func=lambda x: "L2 · distribuição por demanda" if x == "l2" else "Comum · proporcional", disabled=active)
        detector = st.selectbox("Fiscal V2 · comparação", ["effective", "quota", "off"], format_func=lambda x: {"effective": "Concessão efetiva · min(pedido, cota)", "quota": "Cotas anunciadas", "off": "Fiscal desativado"}[x], disabled=active)
        fault = st.selectbox("Cenário", ["healthy", "bias", "replay", "dropout", "double", "starve", "stale"], format_func=lambda x: {"healthy": "Saudável", "bias": "Desvio de orçamento", "replay": "Cota antiga com marca recente", "dropout": "Perda de comunicação", "double": "Concessão duplicada", "starve": "Retirada da cota Y", "stale": "Cota e marca de tempo antigas"}[x], disabled=active)
        profile = st.selectbox("Camadas do modelo", ["coordinator", "actuator", "ideal", "sensors", "nominal", "unlimited"], format_func=lambda x: {"nominal": "Referência sem perturbações", "ideal": "Matemática · atuação imediata", "sensors": "Matemática + sensores", "coordinator": "Sensores + coordenador", "actuator": "Sensores + coordenador + atuadores", "unlimited": "Correção ideal sem teto de atuação"}[x], disabled=active)
        with st.expander("Ajustes do ensaio"):
            fallback = st.checkbox("Ativar reserva após confirmação", value=True, disabled=active or detector == "off")
            fallback_policy = st.selectbox("Política da reserva", ["common", "matched"], format_func=lambda x: "Comum · proporcional imediata" if x == "common" else "Compatível · política e filtro de referência", disabled=active or not fallback or detector == "off")
            st.caption("A reserva compatível acompanha a política e o filtro do caminho de referência independente, incluindo suas tolerâncias.")
            corner = st.selectbox("Tolerâncias", ["nominal", "plus", "minus"], format_func=lambda x: {"nominal": "Nominais", "plus": "Canto positivo", "minus": "Canto negativo"}[x], disabled=active)
            seed = int(st.number_input("Semente reprodutível", 0, 2**31 - 1, 19019, disabled=active))
        samples = total * 0.05 / (dt_us * 1e-6)
        st.caption(f"{number(total * .05, 1)} s de tempo simulado agregado · {number(samples / 1e6, 1)} milhões de avanços de estado.")
        if trajectories == 1 and windows >= 1000:
            st.warning("Esta é uma sequência longa única. Ela pode demorar muito mais que o mesmo número de janelas distribuído em trajetórias paralelas.")
        if total > 10000:
            st.warning("Ensaio maior que 10.000 janelas. Confira o tempo e a memória antes de ampliar o lote.")
        if windows < 7 and fault in ("bias", "dropout", "double", "starve"):
            st.warning("A falha temporária começa em 343,35 ms. Este ensaio termina antes da injeção; use ao menos 7 janelas por trajetória.")
        if total > 2_000_000:
            st.error("Reduza o lote para até 2 milhões de janelas, limite de memória do motor.")
        start = st.button("Iniciar ensaio" if not active else "Ensaio em execução", type="primary", width="stretch", disabled=active or total > 2_000_000)
        st.caption("Os observadores e a interface acompanham o cálculo sem escolher o passo do integrador.")
        if start:
            return Config(dt_us=dt_us, trajectories=trajectories, windows=windows, seed=seed, policy=policy, detector=detector, fallback=fallback and detector != "off", fallback_policy=fallback_policy, fault=fault, profile=profile, corner=corner, trace_points=1200, sequence=sequence, monitor_every=1000)
    return None


def run_labels(runs: list[dict]) -> dict[str, str]:
    """Join compact metadata to research identifiers without changing storage."""
    names = {}
    for path in (STAGE19 / "completed").glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8-sig"))
            name, saved = item["name"], item["path"]
            names[str(saved).replace("\\", "/").casefold()] = name
            names[str(saved).replace("\\", "/").rsplit("/", 1)[-1].casefold()] = name
        except (OSError, ValueError, KeyError, TypeError):
            continue
    labels = {}
    for item in runs:
        path = str(item["path"])
        normalized = path.replace("\\", "/").casefold()
        name = names.get(normalized) or names.get(normalized.rsplit("/", 1)[-1])
        if name:
            labels[path] = name
            continue
        config = item.get("config", {})
        profile = {"ideal": "Imediato", "nominal": "Sem perturbações", "unlimited": "Sem teto", "sensors": "Sensores", "coordinator": "Coordenador", "actuator": "Atuadores"}.get(config.get("profile"), "Ensaio")
        detector = {"effective": "fiscal efetivo", "quota": "fiscal de cotas", "off": "fiscal desligado"}.get(config.get("detector"), "")
        timestamp = time.strftime("%d/%m %H:%M:%S", time.localtime(item.get("mtime", 0)))
        labels[path] = f"{profile} · {config.get('fault', 'healthy')} · {detector} · {number(config.get('dt_us'), 2)} µs · {timestamp}"
    return labels


def stage19_report_panel():
    analysis_path = STAGE19 / "analise.json"
    report_path = STAGE19 / "ETAPA19_RESULTADOS.txt"
    if not analysis_path.exists() or not report_path.exists():
        return
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8-sig"))
        report = report_path.read_text(encoding="utf-8-sig")
    except (OSError, ValueError):
        return
    if analysis.get("status") not in ("complete", "completed"):
        return
    st.subheader("Etapa 19 · resultados auditados")
    counts = analysis.get("counts", {})
    cols = st.columns(4)
    cols[0].metric("Ensaios concluídos", number(counts.get("cases")))
    cols[1].metric("Trajetórias avaliadas", number(counts.get("trajectories")))
    cols[2].metric("Janelas avaliadas", number(counts.get("windows")))
    cols[3].metric("Ensaios de 10.000 janelas", number(counts.get("ensemble_cases")))
    st.caption("Contagem do lote completo. Ensaios comparativos reutilizam as mesmas condições para formar pares; as janelas não são amostras independentes entre si.")
    rows = []
    comparisons = analysis.get("comparisons", {})
    for name, label in [("healthy_quota_to_effective", "Saudável · cotas → efetivo"), ("bias_quota_to_effective", "Desvio · cotas → efetivo")]:
        pair = comparisons.get(name)
        if not isinstance(pair, dict):
            continue
        rows.append({
            "Comparação pareada": label,
            "Janelas": pair.get("windows"),
            "Corretas · cotas": pair.get("baseline_correct"),
            "Corretas · efetivo": pair.get("candidate_correct"),
            "Recuperadas": pair.get("recovered"),
            "Regrediram": pair.get("regressed"),
            "Saldo": pair.get("net"),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    figure = STAGE19 / "comparacao_etapa19.png"
    if figure.exists():
        st.image(str(figure), caption="Comparação da Etapa 19 · figura gerada a partir dos resultados auditados", width="stretch")
    with st.expander("Ler relatório completo e baixar resultados"):
        st.text(report)
        st.download_button("Baixar relatório da Etapa 19", report.encode("utf-8"), file_name=report_path.name, mime="text/plain", key="download_stage19_report")
        st.download_button("Baixar análise estruturada · JSON", analysis_path.read_bytes(), file_name=analysis_path.name, mime="application/json", key="download_stage19_analysis")
    st.divider()


def results_panel():
    stage19_report_panel()
    st.subheader("Caderno de ensaios")
    st.caption("Resultados leves e reproduzíveis. Abra uma execução para ver parâmetros, janelas e curvas.")
    st.button("Atualizar execuções salvas", key="refresh_runs")
    try:
        runs = list_runs()
    except Exception as exc:
        st.warning(f"Não foi possível consultar as execuções: {exc}")
        return
    if not runs:
        st.info("Ainda não há execuções salvas. Ao concluir um ensaio, ele aparecerá aqui.")
        return
    labels = run_labels(runs)
    paths = [str(item["path"]) for item in runs]
    table = []
    for item in runs:
        config, summary = item.get("config", {}), item.get("summary", {})
        table.append({
            "Execução": labels[str(item["path"])],
            "Perfil": config.get("profile", "—"), "Fiscal": config.get("detector", "—"),
            "Falha": config.get("fault", "—"), "Passo (µs)": config.get("dt_us"),
            "Janelas": summary.get("total_windows"), "Corretas": summary.get("correct_windows"),
            "Pico (µA)": choose(summary, "peak_current_uA", "peak_budget_uA"),
            "Alarmes indevidos": summary.get("false_alarm_trajectories"),
        })
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
    selected_path = st.selectbox("Abrir execução", paths, format_func=labels.get, key="saved_run_path")
    selected = paths.index(selected_path)
    try:
        result = load_result(selected_path)
    except Exception as exc:
        st.error(f"Não foi possível abrir a execução: {exc}")
        return
    render_summary(result.get("summary", {}), "saved")
    render_trace(result.get("trace", {}), "saved", budget_uA=result.get("config", {}).get("budget_uA", 90.))
    render_windows(result, "saved")
    with st.expander("Parâmetros e auditoria"):
        st.json({"config": result.get("config"), "timing": result.get("timing"), "validation": result.get("validation"), "arquivo": selected_path})
    if len(runs) >= 2:
        with st.expander("Comparar duas execuções"):
            other_path = st.selectbox("Comparar com", [path for path in paths if path != selected_path], format_func=labels.get, key="compare_run_path")
            other = paths.index(other_path)
            comparison = pd.DataFrame([table[selected], table[other]]).set_index("Execução").T
            comparison = comparison.map(lambda value: number(value, 3) if isinstance(value, (float, np.floating)) else "—" if value is None else str(value))
            st.dataframe(comparison, width="stretch")
            st.caption("Totais diferentes não demonstram causalidade. Compare entradas, sementes, condições iniciais e passos equivalentes; use os pares de janelas para avaliar regressões.")


def reference_panel():
    st.subheader("O ponto de partida · Etapa 18")
    st.caption("Medições preservadas do LTspice. Elas contextualizam a pesquisa; o modelo em Python tem sua própria validação.")
    source = ROOT / "experiments" / "ltspice-caos" / "etapa18"
    try:
        summary = json.loads((source / "resumo.json").read_text(encoding="utf-8-sig"))
        audit = json.loads((source / "verificacao_entrega.json").read_text(encoding="utf-8-sig"))
        trajectories = json.loads((source / "trajetorias.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        st.warning(f"Referência local indisponível: {exc}")
        return
    columns = st.columns(4)
    columns[0].metric("Trajetórias conferidas", number(audit.get("trajetorias")))
    columns[1].metric("Janelas conferidas", number(audit.get("janelas_conferidas_raw")))
    columns[2].metric("Critério legado de corrente", f"{number(audit.get('checagens_corrente_aprovadas'))} / {number(audit.get('trajetorias'))}")
    columns[3].metric("Convergência numérica", "Em aberto")
    st.caption("Aprovação do critério legado: pico até 100,005 µA. Isso não certifica um teto físico estrito de 90 µA.")
    st.markdown("#### Fiscal V2 no L2 rápido")
    candidate = next((item for item in summary if item.get("arquivo") == "L2_5_10_v2"), {})
    columns = st.columns(3)
    columns[0].metric("Recuperação lógica", f"{number(candidate.get('corretas'))} / {number(candidate.get('janelas'))}")
    candidate_false = sum(bool(item.get("cota_alarme_indevido")) for item in trajectories if item.get("arquivo") == "L2_5_10_v2")
    columns[1].metric("Sinais indevidos · fiscal de cotas", number(candidate_false))
    columns[2].metric("Trajetórias deste ensaio", number(candidate.get("trajetorias")))
    st.markdown('<div class="lab-note">A Etapa 19 testa se comparar a <b>concessão efetiva</b> reduz alarmes causados por cotas que mudam sem limitar o pedido. Heartbeat, idade, faixa e soma das cotas continuam sendo verificações separadas.</div>', unsafe_allow_html=True)
    frame = pd.DataFrame(summary)
    frame["cota_sinais_indevidos"] = frame["arquivo"].map(lambda name: sum(bool(item.get("cota_alarme_indevido")) for item in trajectories if item.get("arquivo") == name))
    keep = [name for name in ["arquivo", "trajetorias", "corretas", "janelas", "cota_sinais_indevidos", "alarmes_indevidos", "pico_corrente_uA", "rms_residuo_y_uA", "rms_residuo_d_uA", "variacao_g_por_s"] if name in frame]
    st.markdown("#### Comparação dos ensaios preservados")
    st.dataframe(frame[keep].rename(columns={"arquivo": "Ensaio", "trajetorias": "Trajetórias", "corretas": "Corretas", "janelas": "Janelas", "cota_sinais_indevidos": "Sinais indevidos · cotas", "alarmes_indevidos": "Alarmes indevidos · topo", "pico_corrente_uA": "Pico por shunt (µA)", "rms_residuo_y_uA": "Resíduo Y (µA)", "rms_residuo_d_uA": "Resíduo D (µA)", "variacao_g_por_s": "Variação g / s"}), width="stretch", hide_index=True)
    st.caption("Cotas e topo são detectores diferentes. A contagem de sinais de cotas inclui os controles em que a reserva estava desativada.")
    with st.expander("Limites desta comparação"):
        st.write("O LTspice usa integração adaptativa e modelos de circuito. O ChaosLab usa passos fixos e camadas matemáticas explícitas. Uma melhoria no ChaosLab é evidência sobre essas equações e hipóteses; ainda precisa ser levada de volta ao circuito.")
        st.write("As 45 medições pertencem à arquitetura conceitual. O laboratório não representa uma PCB, chips físicos, térmica, parasitas ou interferência eletromagnética.")
        st.caption(f"Fontes: {source / 'resumo.json'}, trajetorias.json e verificacao_entrega.json.")


@st.cache_data(ttl=30, show_spinner=False)
def cached_disk_status():
    return disk_status()


def storage_panel():
    st.subheader("Armazenamento sob controle")
    st.caption("O cálculo mantém estatísticas acumuladas e traçados limitados. Cada ensaio salva métricas e amostras, sem despejar todos os passos em disco.")
    try:
        status = cached_disk_status()
    except Exception as exc:
        st.warning(f"Não foi possível medir o armazenamento: {exc}")
        return
    columns = st.columns(3)
    columns[0].metric("Espaço livre no disco", f"{number(status.get('free_gb'), 1)} GB")
    columns[1].metric("Pasta da pesquisa", f"{number(status.get('project_gb'), 2)} GB")
    columns[2].metric("Resultados do ChaosLab", f"{number(status.get('results_mb'), 2)} MB")
    limit = status.get("max_results_mb", 0)
    used = status.get("results_mb", 0)
    if limit:
        st.progress(min(1.0, max(0.0, used / limit)), text=f"{number(used, 1)} de {number(limit)} MB reservados para resultados")
    st.write(f"Reserva mínima de espaço livre: **{number(status.get('min_free_gb'), 1)} GB**.")
    st.info("Os arquivos de entrada e os resultados de pesquisa são preservados. Se o limite impedir uma gravação, o painel mantém o resultado atual em memória e informa o motivo.")
    cleanup_path = ROOT / "experiments" / "ltspice-caos" / "manutencao_armazenamento" / "limpeza_executada.json"
    try:
        cleanup = json.loads(cleanup_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        cleanup = None
    if cleanup:
        st.markdown("#### Limpeza da pesquisa")
        columns = st.columns(3)
        columns[0].metric("Arquivos pesados removidos", f"{number(cleanup.get('bytes_removed', 0) / 1e9, 2)} GB")
        columns[1].metric("Casos com traçado compacto", number(cleanup.get("exported_cases")))
        columns[2].metric("Traçados RAW mantidos", number(cleanup.get("retained_raw")))
        st.caption(f"Aumento observado de espaço livre durante a limpeza: {number(cleanup.get('observed_free_delta_bytes', 0) / 1e9, 2)} GB. O uso por outros processos pode mudar esse valor.")
        with st.expander("Registro da limpeza e retenção"):
            note = cleanup_path.with_name("NOTA_RETENCAO.txt")
            if note.exists():
                st.text(note.read_text(encoding="utf-8-sig"))
            st.caption(f"Manifesto: {cleanup_path}")
    with st.expander("O que é preservado em um ensaio"):
        st.write("Configuração e semente, resumo de métricas, classificação de cada janela, medidas por trajetória, um traçado amostrado, tempo de execução e verificações do cálculo.")
        st.write("Os gráficos são uma amostra visual. O resumo de picos, resíduos e recuperação usa todos os passos executados.")


def main():
    config = sidebar()
    st.markdown('<div class="lab-eyebrow">PESQUISA VIOLETA / ETAPA 19</div>', unsafe_allow_html=True)
    st.title("ChaosLab")
    st.markdown('<div class="lab-subtitle">Um laboratório para observar o caos com o relógio sob controle.<br>Equações, concessões e recuperação lógica — acompanhadas durante o cálculo.</div>', unsafe_allow_html=True)
    st.markdown('<span class="lab-pill">Passos fixos</span><span class="lab-pill">Orçamento nominal · 90 µA</span><span class="lab-pill">Reserva E · até 5 µA do mesmo orçamento</span>', unsafe_allow_html=True)
    if config:
        st.session_state["chaoslab_job"] = new_job(config)
        st.rerun()
    laboratory, results, reference, storage, tools = st.tabs(["Laboratório", "Resultados", "Referência · Etapa 18", "Armazenamento", "Ferramentas"])
    with laboratory:
        st.subheader("Acompanhar o ensaio")
        batch_panel()
        live_panel()
        with st.expander("Como interpretar o laboratório"):
            st.write("Uma janela lógica dura 50 ms. A avaliação verifica o sinal de X durante o trecho de 30 a 49 ms de cada janela. As trajetórias continuam de uma janela para a seguinte, sem reiniciar o estado.")
            st.write("O lote de 10.000 janelas usa 500 trajetórias com 20 janelas cada: 500 s de tempo simulado agregado. Uma trajetória única de 10.000 janelas tem outra história dinâmica e outro custo; selecione o modo personalizado para esse experimento.")
            st.write("Passos fixos retiram dos observadores a escolha do instante de integração. O erro de discretização continua existindo: compare passos menores, margens lógicas e medidas agregadas antes de concluir convergência.")
            st.write("O fiscal compara concessões efetivas ou cotas e mantém as guardas de comunicação. Ativar a reserva altera legitimamente a dinâmica. Observar ou desenhar um gráfico não altera o relógio do cálculo.")
    with results:
        results_panel()
    with reference:
        reference_panel()
    with storage:
        storage_panel()
    with tools:
        from chaoslab.tools_ui import render_tools
        render_tools()
    st.caption("CHAOSLAB · Experimentos locais e reproduzíveis · Resultados matemáticos ainda sujeitos à validação no LTspice")


if __name__ == "__main__":
    main()
