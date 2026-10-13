"""Compact, bounded result storage. Inputs and historical experiments are never pruned."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "chaoslab" / "results"
MAX_RESULTS_MB = 512
MAX_RUN_MB = 32
MIN_FREE_GB = 10
_LOCK = threading.Lock()


@contextmanager
def _process_lock():
    """Serialize quota checks across CLI workers and the dashboard process."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / ".storage.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        if os.name == "nt":
            import msvcrt
            deadline = time.monotonic() + 20
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise OSError("Outra gravação mantém o armazenamento ocupado.")
                    time.sleep(.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for directory, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not Path(directory, d).is_symlink()]
        for name in files:
            p = Path(directory, name)
            try:
                if not p.is_symlink():
                    total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total


def disk_status() -> dict:
    return dict(free_gb=shutil.disk_usage(ROOT).free / 1e9,
                project_gb=_size(ROOT) / 1e9,
                results_mb=_size(RESULTS) / 1e6,
                max_results_mb=MAX_RESULTS_MB, min_free_gb=MIN_FREE_GB,
                max_run_mb=MAX_RUN_MB)


def _atomic(path: Path, data: bytes) -> None:
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # Windows readers may briefly omit FILE_SHARE_DELETE. Retry publication
        # without changing the already computed result or truncating the target.
        for attempt in range(100):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 99:
                    raise
                time.sleep(.02)
    finally:
        temp.unlink(missing_ok=True)


def save_result(result: dict) -> str:
    """Save complete output as gzip JSON plus small index; fail closed on quota."""
    if result.get("status", "completed") not in ("completed", "complete"):
        raise ValueError("Somente execuções concluídas podem ser salvas como resultado.")
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    packed = gzip.compress(payload, compresslevel=6, mtime=0)
    if len(packed) > MAX_RUN_MB * 1e6:
        raise OSError("Resultado excede o limite de 32 MB por execução.")
    with _LOCK, _process_lock():
        RESULTS.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(ROOT).free - len(packed) < MIN_FREE_GB * 1e9:
            raise OSError("Reserva de 10 GB atingida; resultado permanece em memória.")
        if _size(RESULTS) + len(packed) > MAX_RESULTS_MB * 1e6:
            raise OSError("Cota de 512 MB de resultados atingida. Exporte/limpe execuções antigas.")
        digest = hashlib.sha256(payload).hexdigest()
        name = time.strftime("%Y%m%d-%H%M%S") + "-" + digest[:10] + "-" + uuid.uuid4().hex[:6]
        target = RESULTS / (name + ".json.gz")
        _atomic(target, packed)
        metadata = dict(path=str(target), summary=result.get("summary", {}),
                        config=result.get("config", {}), sha256_json=digest,
                        bytes=len(packed), mtime=time.time(), schema="chaoslab-result-v1")
        _atomic(RESULTS / (name + ".meta.json"),
                json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8"))
    return str(target)


def list_runs() -> list[dict]:
    found = []
    for path in RESULTS.glob("*.meta.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if Path(item["path"]).exists():
                found.append(item)
        except (ValueError, KeyError, OSError):
            continue
    return sorted(found, key=lambda x: x["mtime"], reverse=True)


def load_result(path: str | Path) -> dict:
    p = Path(path).resolve()
    if not p.is_relative_to(ROOT) or p.is_symlink():
        raise ValueError("Resultado deve pertencer à pasta Violeta.")
    if p.stat().st_size > MAX_RUN_MB * 1e6:
        raise ValueError("Arquivo excede a cota de leitura.")
    with gzip.open(p, "rt", encoding="utf-8") as f:
        result = json.load(f)
    return result
