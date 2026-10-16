import json
from pathlib import Path
import pytest
from chaoslab import notebook


@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(notebook,'ROOT',tmp_path);monkeypatch.setattr(notebook,'MIN_FREE_GB',0)
    p=tmp_path/'evidence.json';p.write_text('{"value":1}')
    return p


def record(path,**kw):return notebook.record_experiment(hypothesis='Test hypothesis',configuration={'h':5},result_references=[path],**kw)


def test_roundtrip_references_and_append_only_conclusion(isolated):
    identifier=record(isolated)
    read=notebook.read_entry(identifier)
    assert read['verification']['references_ok']
    assert len(notebook.list_entries())==1
    newer=notebook.append_conclusion(identifier,'Measured result, limited scope')
    assert notebook.read_entry(newer)['parent_id']==identifier
    assert notebook.read_entry(identifier)['conclusion']==''


def test_tampering_and_missing_evidence(isolated):
    identifier=record(isolated)
    isolated.write_text('changed')
    assert not notebook.read_entry(identifier)['verification']['references_ok']
    with pytest.raises(ValueError):notebook.append_conclusion(identifier,'Changed reference')
    isolated.unlink()
    assert notebook.read_entry(identifier)['verification']['issues'][0]['issue']=='missing'
    p=notebook.directory()/(identifier+'.json');r=json.loads(p.read_text());r['hypothesis']='changed';p.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='integrity'):notebook.read_entry(identifier)
    assert notebook.list_entries()[0]['record_ok'] is False


def test_path_scope_and_quotas(isolated,monkeypatch):
    with pytest.raises(ValueError):notebook.read_entry('../../outside')
    with pytest.raises(ValueError):record(isolated.parent.parent/'outside.json')
    with pytest.raises(ValueError):record(isolated,evidence={'bad':float('nan')})
    monkeypatch.setattr(notebook,'MAX_ENTRY_BYTES',20)
    with pytest.raises(ValueError,match='2 MiB'):record(isolated)
    monkeypatch.setattr(notebook,'MAX_ENTRY_BYTES',2*1024**2);monkeypatch.setattr(notebook,'MAX_TOTAL_BYTES',0)
    with pytest.raises(OSError,match='quota'):record(isolated)
