"""Immutable, compact experiment records with verifiable local references.

Hashes detect accidental changes, not malicious replacement of both record and
hash. No credentials, model calls, automatic pruning or external publication.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid

from chaoslab.storage import ROOT,_atomic,_process_lock,_size,MIN_FREE_GB

MAX_ENTRY_BYTES=2*1024**2
MAX_TOTAL_BYTES=64*1024**2
MAX_REFERENCE_BYTES=32*1024**2


def directory():
    path=(ROOT/'chaoslab/notebook_entries').resolve()
    if not path.is_relative_to(ROOT.resolve()):raise ValueError('Notebook directory escapes project')
    return path


def _encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')


def _hash(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _reference(path,require_exists=True):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    resolved=path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or resolved==ROOT.resolve():
        raise ValueError('Reference must be a file inside this project')
    if require_exists:
        if not resolved.is_file():raise ValueError('Referenced evidence is missing')
        if resolved.stat().st_size>MAX_REFERENCE_BYTES:raise ValueError('Reference is not compact (over 32 MiB)')
    return resolved


def _record_path(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'[0-9]{8}T[0-9]{12}Z-[0-9a-f]{12}',identifier):
        raise ValueError('Invalid notebook identifier')
    path=(directory()/(identifier+'.json')).resolve()
    if path.parent!=directory():raise ValueError('Record path escapes notebook')
    return path


def record_experiment(*,hypothesis,configuration,result_references=(),conclusion='',status='complete',evidence=None,parent_id=None):
    if not isinstance(hypothesis,str) or not 1<=len(hypothesis.strip())<=8000:
        raise ValueError('Hypothesis requires 1..8000 characters')
    if not isinstance(conclusion,str) or len(conclusion)>16000:raise ValueError('Conclusion too large')
    if status not in ('complete','cancelled','failed','note'):raise ValueError('Invalid experiment status')
    if not isinstance(configuration,(dict,list)):raise ValueError('Configuration must be a JSON object or list')
    if len(result_references)>100:raise ValueError('At most 100 compact references')
    if parent_id is not None:read_entry(parent_id,verify_references=False)
    references=[]
    for raw in result_references:
        path=_reference(raw)
        references.append(dict(path=path.relative_to(ROOT.resolve()).as_posix(),bytes=path.stat().st_size,sha256=_hash(path)))
    sources={}
    for name in ('core.py','engine.py','workbenches.py','bridge.py','diagnostics.py','notebook.py'):
        path=ROOT/'chaoslab'/name
        if path.is_file():sources[name]=_hash(path)
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:12]
    record=dict(schema='chaoslab-notebook-v1',id=identifier,created_utc=datetime.now(timezone.utc).isoformat(),
        hypothesis=hypothesis.strip(),configuration=configuration,conclusion=conclusion,status=status,
        sources_sha256=sources,references=references,evidence=evidence or {},parent_id=parent_id)
    record['record_sha256']=hashlib.sha256(_encoded(record)).hexdigest()
    payload=_encoded(record)
    if len(payload)>MAX_ENTRY_BYTES:raise ValueError('Record exceeds 2 MiB; store compact summaries/references')
    with _process_lock():
        folder=directory();folder.mkdir(parents=True,exist_ok=True)
        if _size(folder)+len(payload)>MAX_TOTAL_BYTES:raise OSError('Notebook quota of 64 MiB reached')
        if shutil.disk_usage(ROOT).free-len(payload)<MIN_FREE_GB*1e9:raise OSError('Free disk reserve reached')
        target=_record_path(identifier)
        if target.exists():raise FileExistsError('Immutable record already exists')
        _atomic(target,payload)
    return identifier


def read_entry(identifier,verify_references=True):
    path=_record_path(identifier)
    if path.stat().st_size>MAX_ENTRY_BYTES:raise ValueError('Oversized notebook record')
    record=json.loads(path.read_text(encoding='utf-8'))
    if record.get('id')!=identifier or record.get('schema')!='chaoslab-notebook-v1':raise ValueError('Record identity mismatch')
    expected=record.get('record_sha256')
    unsigned={k:v for k,v in record.items() if k!='record_sha256'}
    if hashlib.sha256(_encoded(unsigned)).hexdigest()!=expected:raise ValueError('Notebook integrity check failed')
    issues=[]
    if verify_references:
        for reference in record['references']:
            p=_reference(reference['path'],require_exists=False)
            if not p.is_file():issues.append(dict(path=reference['path'],issue='missing'))
            elif p.stat().st_size!=reference['bytes']:issues.append(dict(path=reference['path'],issue='size_changed'))
            elif _hash(p)!=reference['sha256']:issues.append(dict(path=reference['path'],issue='hash_changed'))
    return dict(record,verification=dict(record_ok=True,references_checked=verify_references,
                references_ok=not issues if verify_references else None,issues=issues))


def list_entries(limit=200):
    if not isinstance(limit,int) or not 1<=limit<=1000:raise ValueError('Limit must be 1..1000')
    entries=[]
    for p in sorted(directory().glob('*.json'),reverse=True)[:limit]:
        try:
            r=read_entry(p.stem,verify_references=False)
            entries.append(dict(id=r['id'],created_utc=r['created_utc'],hypothesis=r['hypothesis'],
                status=r['status'],references=len(r['references']),record_ok=True))
        except (ValueError,OSError,TypeError,KeyError):
            entries.append(dict(id=p.stem,status='invalid',record_ok=False))
    return entries


def append_conclusion(identifier,conclusion):
    original=read_entry(identifier)
    if not original['verification']['references_ok']:
        raise ValueError('Evidence changed or is missing; restore/resolve references before annotating')
    return record_experiment(hypothesis=original['hypothesis'],configuration=original['configuration'],
        result_references=[r['path'] for r in original['references']],conclusion=conclusion,
        status='note',evidence=original['evidence'],parent_id=identifier)
