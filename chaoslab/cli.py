"""Run a reproducible experiment without requiring the Streamlit server."""
from __future__ import annotations
import argparse
from dataclasses import fields
import json
from pathlib import Path
import time
from chaoslab.core import Config, run
from chaoslab.storage import save_result


def main() -> None:
    parser = argparse.ArgumentParser(description="ChaosLab — lote NumPy de passo fixo")
    parser.add_argument("--config", type=Path, help="Configuração JSON")
    parser.add_argument("--name", default="manual")
    parser.add_argument("--progress", type=Path, help="Instantâneo leve para acompanhamento")
    args = parser.parse_args()
    data = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    allowed = {f.name for f in fields(Config)}
    unexpected = set(data) - allowed
    if unexpected:
        parser.error(f"Campos desconhecidos: {sorted(unexpected)}")
    last = 0.0

    def progress(snapshot):
        nonlocal last
        now = time.monotonic()
        if now - last < 3 and snapshot.get("fraction", 0) < 1:
            return
        last = now
        small = {k: v for k, v in snapshot.items() if k != "trace"}
        print(json.dumps(small, ensure_ascii=False), flush=True)
        if args.progress:
            args.progress.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.progress.with_suffix(".tmp")
            temporary.write_text(json.dumps(small), encoding="utf-8")
            temporary.replace(args.progress)

    result = run(Config(**data), progress=progress)
    result["name"] = args.name
    path = save_result(result)
    print(json.dumps({"saved": path, "summary": result["summary"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
