import gzip
import json
from pathlib import Path
import pytest
from chaoslab import storage


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "ROOT", tmp_path)
    monkeypatch.setattr(storage, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(storage, "MIN_FREE_GB", 0)
    return tmp_path


def test_roundtrip_and_index(isolated):
    result = {"status": "completed", "summary": {"total_windows": 10000},
              "config": {"dt_us": 5}, "trace": {"x": [1.0, -1.0]}}
    path = storage.save_result(result)
    assert storage.load_result(path) == result
    index = storage.list_runs()
    assert len(index) == 1 and index[0]["summary"]["total_windows"] == 10000
    assert not list(isolated.rglob("*.tmp"))


def test_quota_does_not_delete_existing(isolated, monkeypatch):
    path = storage.save_result({"summary": {}, "trace": {"x": [1]}})
    original = Path(path).read_bytes()
    monkeypatch.setattr(storage, "MAX_RESULTS_MB", 0)
    with pytest.raises(OSError, match="512 MB"):
        storage.save_result({"summary": {}})
    assert Path(path).read_bytes() == original
    assert len(storage.list_runs()) == 1


def test_cancelled_and_nonfinite_not_saved(isolated):
    with pytest.raises(ValueError):
        storage.save_result({"status": "cancelled"})
    with pytest.raises(ValueError):
        storage.save_result({"summary": {"bad": float("nan")}})
    assert not storage.list_runs()


def test_read_is_scoped(isolated):
    with pytest.raises(ValueError):
        storage.load_result(isolated.parent / "unrelated.json.gz")


def test_atomic_publish_retries_windows_reader_lock(isolated, monkeypatch):
    actual = storage.os.replace
    calls = []
    def temporary_lock(source, target):
        calls.append((source, target))
        if len(calls) < 3:
            raise PermissionError("simulated reader without share-delete")
        return actual(source, target)
    monkeypatch.setattr(storage.os, "replace", temporary_lock)
    target = isolated / "progress.json"
    target.write_bytes(b"previous")
    storage._atomic(target, b"new complete snapshot")
    assert target.read_bytes() == b"new complete snapshot"
    assert len(calls) == 3 and not list(isolated.glob("*.tmp"))


def test_decompression_is_bounded(isolated, monkeypatch):
    path=storage.save_result({'summary':{},'padding':'a'*200})
    monkeypatch.setattr(storage,'MAX_UNPACKED_MB',0)
    with pytest.raises(ValueError,match='descomprimido'):storage.load_result(path)
