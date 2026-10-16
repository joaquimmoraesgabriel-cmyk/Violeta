"""Explicit nominal-MLC interchange; never claims to export physical controllers.

make_manifest(config_or_result, trajectory=0), export_bundle(manifest, directory),
import_csv(path_or_bytes), import_raw(path_or_bytes), compare(trace_a, trace_b).
All times are seconds, states volts, optional currents microamperes in memory.
"""
from __future__ import annotations

from dataclasses import asdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import zipfile

import numpy as np

from chaoslab.engine import Config, _sequence
from chaoslab.storage import ROOT, _atomic, _process_lock, _size, MIN_FREE_GB

MAX_BYTES=32*1024**2
MAX_POINTS=500000
MAX_EXPORT_BYTES=128*1024**2
PHYSICS=dict(capacitance_F=1e-6,scale_s=100e-6,g_outer=-.55,g_inner=-1.02,
             g_break_V=1.,damping=1.015,offset=-.005,logic_amplitude=.005,
             forcing_amplitude=.11,forcing_omega_scaled=.74)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def make_manifest(config_or_result, trajectory=0):
    result=config_or_result if isinstance(config_or_result,dict) and 'config' in config_or_result else None
    raw=result['config'] if result else config_or_result
    cfg=Config(**raw) if isinstance(raw,dict) else raw
    cfg.validate()
    if cfg.profile!='nominal':
        raise ValueError('Esta exportação representa somente profile=nominal; controlador fechado não foi exportado.')
    if not isinstance(trajectory,int) or not 0<=trajectory<cfg.trajectories:
        raise ValueError('Trajetória inválida')
    if cfg.fault!='healthy' or cfg.additional_faults:
        raise ValueError('Referência nominal não exporta falhas do coordenador')
    rng=np.random.default_rng(np.random.SeedSequence([cfg.seed,191]))
    states=rng.uniform(-.37,.37,cfg.trajectories);states[0]=-.37
    if len(states)>1:states[1]=.37
    if cfg.initial_x: states=np.asarray(cfg.initial_x)
    codes=_sequence(cfg).tolist()
    if (cfg.duration_s or cfg.windows*.05)/(cfg.dt_us*1e-6)>250000:
        raise ValueError('Export would require over 250000 minimum steps; choose a shorter nominal validation horizon')
    manifest=dict(schema='chaoslab-ltspice-nominal-v1',model='MLC nominal ODE',
        config=asdict(cfg),trajectory=trajectory,
        initial=dict(x_V=float(states[trajectory]),y_V=cfg.initial_y),
        inputs=dict(codes=codes,block_s=.05,edge_s=1e-6),physics=PHYSICS.copy(),
        duration_s=cfg.duration_s or cfg.windows*.05,max_step_s=cfg.dt_us*1e-6,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitation='Nominal mathematical plant only; LTspice uses an adaptive grid and can save more points than the minimum step estimate. No fiscal, allocator, actuator chip or PCB is exported.')
    if result:
        manifest['python_final_state_sha256']=result['validation']['final_state_sha256']
        expected=result['per_trajectory'][trajectory]
        if (expected['initial_x'],expected['initial_y'])!=(manifest['initial']['x_V'],manifest['initial']['y_V']):
            raise ValueError('Initial states differ from recorded result')
        if result['validation']['input_sequence']!=codes: raise ValueError('Input sequence differs from result')
    manifest['manifest_sha256']=digest(manifest)
    return manifest


def validate_manifest(m):
    if not isinstance(m,dict) or m.get('schema')!='chaoslab-ltspice-nominal-v1':
        raise ValueError('Unsupported manifest schema')
    unsigned={k:v for k,v in m.items() if k!='manifest_sha256'}
    if digest(unsigned)!=m.get('manifest_sha256'):raise ValueError('Manifest integrity check failed')
    expected=make_manifest(m['config'],m['trajectory'])
    for key in ('initial','inputs','physics','duration_s','max_step_s','model'):
        if m.get(key)!=expected[key]:raise ValueError('Inconsistent manifest: '+key)
    return m


def _pwl(codes,bit,duration):
    values=[(0.,(codes[0]>>bit)&1)]
    for i,code in enumerate(codes[1:],1):
        t=i*.05
        if t>=duration:break
        old=(codes[i-1]>>bit)&1; new=(code>>bit)&1
        values.append((t,old));values.append((min(t+1e-6,duration),new))
    if values[-1][0]<duration: values.append((duration,values[-1][1]))
    return ' '.join(f'{t:.17g} {v}' for t,v in values)


def netlist(m):
    validate_manifest(m)
    p=m['physics'];ini=m['initial'];duration=m['duration_s']
    return f'''* ChaosLab nominal MLC; shared manifest {m['manifest_sha256']}
* Mathematical reference only. LTspice adaptive integration, no controller chips.
.param cap={p['capacitance_F']:.17g} scale={p['scale_s']:.17g}
.func gx(z) {{({p['g_outer']})*z+({p['g_inner']}-{p['g_outer']})/2*(abs(z+1)-abs(z-1))}}
Va a 0 PWL({_pwl(m['inputs']['codes'],1,duration)})
Vb b 0 PWL({_pwl(m['inputs']['codes'],0,duration)})
Cx x 0 {{cap}} IC={ini['x_V']:.17g}
Cy y 0 {{cap}} IC={ini['y_V']:.17g}
.ic V(x)={ini['x_V']:.17g} V(y)={ini['y_V']:.17g}
Bx 0 x I={{cap/scale*(V(y)-gx(V(x)))}}
By 0 y I={{cap/scale*(-1.015*V(y)-V(x)-0.005+0.005*(2*V(a)-1+2*V(b)-1)+0.11*sin(0.74*time/scale))}}
.options plotwinsize=0 reltol=1e-8 abstol=1e-12 vntol=1e-10
.save V(x) V(y) V(a) V(b)
.tran 0 {duration:.17g} 0 {m['max_step_s']:.17g}
.end
'''


def export_bundle(manifest,directory):
    validate_manifest(manifest)
    target=Path(directory).resolve();allowed=(ROOT/'chaoslab/bridge_exports').resolve()
    if not allowed.is_relative_to(ROOT.resolve()) or not target.is_relative_to(allowed) or target==allowed:
        raise ValueError('Export must be in a new subdirectory of chaoslab/bridge_exports')
    encoded=json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False).encode()
    cir=netlist(manifest).encode('ascii')
    if len(encoded)+len(cir)>MAX_BYTES:raise ValueError('Export exceeds size cap')
    with _process_lock():
        if target.exists(): raise ValueError('Export directory already exists; existing evidence is preserved')
        if _size(allowed)+len(encoded)+len(cir)>MAX_EXPORT_BYTES:raise ValueError('Bridge export quota reached')
        if shutil.disk_usage(ROOT).free-len(encoded)-len(cir)<MIN_FREE_GB*1e9:raise OSError('Minimum free disk reserve reached')
        target.mkdir(parents=True)
        _atomic(target/'manifest.json',encoded);_atomic(target/'nominal.cir',cir)
    return dict(directory=str(target),manifest=str(target/'manifest.json'),netlist=str(target/'nominal.cir'))


def bundle_zip(manifest):
    validate_manifest(manifest)
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr('nominal.cir',netlist(manifest))
    return data.getvalue()


def _bytes(source):
    if isinstance(source,bytes):data=source
    else:
        p=Path(source)
        if p.stat().st_size>MAX_BYTES:raise ValueError('Import exceeds 32 MiB')
        data=p.read_bytes()
    if not data or len(data)>MAX_BYTES:raise ValueError('Empty import or over 32 MiB')
    return data


def validate_trace(trace):
    if not isinstance(trace,dict) or not {'t_s','x','y'}<=trace.keys():raise ValueError('Required time/x/y channels missing')
    n=len(trace['t_s'])
    if not 2<=n<=MAX_POINTS:raise ValueError('Use 2..500000 samples')
    clean={}
    for key,values in trace.items():
        arr=np.asarray(values,dtype=float)
        if arr.ndim!=1 or len(arr)!=n or not np.isfinite(arr).all():raise ValueError('Invalid/nonfinite channel: '+key)
        clean[key]=arr
    if clean['t_s'][0]<0 or np.any(np.diff(clean['t_s'])<=0):
        raise ValueError('Time must be nonnegative and strictly increasing; separate stepped simulations')
    return clean


ALIASES={'time':('t_s',1.),'t_s':('t_s',1.),'v(x)':('x',1.),'x':('x',1.),
         'v(y)':('y',1.),'y':('y',1.),'v(a)':('input_a',1.),'v(b)':('input_b',1.),
         'current_y_ua':('current_y_uA',1.),'current_d_ua':('current_d_uA',1.),
         'current_e_ua':('current_e_uA',1.)}


def import_csv(source):
    data=_bytes(source)
    try:text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError as exc:raise ValueError('CSV must be UTF-8 or UTF-16') from exc
    lines=text.splitlines()
    if not lines:raise ValueError('Empty CSV')
    first=lines[0]
    delimiter='\t' if '\t' in first else ',' if ',' in first else ';' if ';' in first else None
    rows=csv.reader(lines,delimiter=delimiter) if delimiter else (re.split(r'\s+',line.strip()) for line in lines)
    header=[x.strip().lower() for x in next(rows)]
    indices={}
    for i,key in enumerate(header):
        if key in ALIASES:
            name,factor=ALIASES[key]
            if name in indices:raise ValueError('Duplicate channel: '+name)
            indices[name]=(i,factor)
    if not {'t_s','x','y'}<=indices.keys():raise ValueError('CSV needs time, V(x), V(y), in seconds/volts')
    columns={key:[] for key in indices}
    for row in rows:
        if not row or all(not x.strip() for x in row):continue
        if len(columns['t_s'])>=MAX_POINTS:raise ValueError('Too many CSV samples')
        if len(row)!=len(header):raise ValueError('CSV row width differs from header')
        try:
            for key,(i,factor) in indices.items():columns[key].append(float(row[i])*factor)
        except ValueError as exc:raise ValueError('CSV contains nonnumeric values') from exc
    clean=validate_trace(columns)
    return dict(trace={k:v.tolist() for k,v in clean.items()},source_sha256=hashlib.sha256(data).hexdigest(),
                format='CSV/TSV',units='seconds, volts; explicit *_uA channels in microamperes')


def import_raw(source):
    """Bounded single-run transient RAW, UTF-16/UTF-8, real interleaved data only."""
    data=_bytes(source);header=None
    for encoding in ('utf-16-le','utf-8'):
        for ending in ('\n','\r\n'):
            marker=('Binary:'+ending).encode(encoding);position=data[:65536].find(marker)
            if position>=0:
                header=data[:position].decode(encoding).lstrip('\ufeff');offset=position+len(marker);break
        if header is not None:break
    if header is None:raise ValueError('Unsupported RAW header; use binary transient or export CSV')
    flags_match=re.search(r'^Flags:\s*(.+)',header,re.M)
    flags=flags_match[1].strip().lower().split() if flags_match else []
    if 'real' not in flags or any(x in flags for x in ('complex','fastaccess','stepped')):
        raise ValueError('Only a single real interleaved transient is supported')
    nm=re.search(r'No\. Variables:\s*(\d+)',header);np_=re.search(r'No\. Points:\s*(\d+)',header)
    if not nm or not np_:raise ValueError('RAW counts missing')
    nv,points=int(nm[1]),int(np_[1])
    if not 3<=nv<=128 or not 2<=points<=MAX_POINTS:raise ValueError('RAW count exceeds import limits')
    names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',header,re.M)
    if len(names)!=nv or names[0].lower()!='time':raise ValueError('Invalid RAW variable table')
    dtype=np.dtype([('t','<f8'),('v','<f8' if 'double' in flags else '<f4',(nv-1,))])
    if len(data)-offset!=points*dtype.itemsize:raise ValueError('Truncated RAW or unsupported numeric precision')
    arr=np.frombuffer(data,dtype=dtype,count=points,offset=offset)
    trace={'t_s':arr['t']}
    for i,name in enumerate(names[1:]):
        if name.lower() in ALIASES:
            key,factor=ALIASES[name.lower()]
            if key in trace:raise ValueError('Duplicate RAW channel')
            trace[key]=arr['v'][:,i].astype(float)*factor
    clean=validate_trace(trace)
    return dict(trace={k:v.tolist() for k,v in clean.items()},source_sha256=hashlib.sha256(data).hexdigest(),
                format='LTspice binary RAW',units='seconds and volts')


def compare(a,b):
    a,b=validate_trace(a),validate_trace(b)
    lo=max(a['t_s'][0],b['t_s'][0]);hi=min(a['t_s'][-1],b['t_s'][-1])
    times=a['t_s'][(a['t_s']>=lo)&(a['t_s']<=hi)]
    if len(times)<2:raise ValueError('No usable overlap; extrapolation is not permitted')
    channels={};overlay={'t_s':times.tolist()}
    for key in sorted((a.keys()&b.keys())-{'t_s'}):
        av=np.interp(times,a['t_s'],a[key]);bv=np.interp(times,b['t_s'],b[key]);delta=bv-av
        channels[key]=dict(rms=float(np.sqrt(np.mean(delta**2))),max_abs=float(np.max(np.abs(delta))))
        overlay[key+'_python']=av.tolist();overlay[key+'_ltspice']=bv.tolist()
    return dict(interval_s=[float(times[0]),float(times[-1])],samples=len(times),channels=channels,overlay=overlay,
        limitation='Only overlapping recorded samples; interpolation and different integrators remain. This comparison does not establish physical circuit equivalence.')


def logical_comparison(result,imported_trace,trajectory=0):
    """Compare raw imported node extrema against exact saved Python windows.

    Assumes the imported circuit used the selected Python input protocol. Does
    not infer that fact from a waveform or from a matching number of samples.
    """
    trace=validate_trace(imported_trace);t=trace['t_s'];x=trace['x'];rows=[];missing=[]
    for row in result['windows']:
        if row['trajectory']!=trajectory:continue
        left,right=row['window_start_s'],row['window_end_s']
        if t[0]>left or t[-1]<right:
            missing.append(row['window']);continue
        inside=x[(t>=left)&(t<=right)]
        values=np.r_[np.interp(left,t,x),inside,np.interp(right,t,x)]
        lo,hi=float(values.min()),float(values.max())
        margin=lo if row['expected'] else -hi;correct=margin>0
        rows.append(dict(window=row['window'],input=row['input'],python_margin=row['margin'],
            ltspice_margin=margin,python_correct=row['correct'],ltspice_correct=correct,
            discordant=row['correct']!=correct))
    return dict(windows=rows,incomplete_windows=missing,compared=len(rows),
        discordant=sum(r['discordant'] for r in rows),
        assumption='Uses the selected Python input protocol; verify the LTspice manifest. Raw nodes plus interpolated interval endpoints; between-node extrema unresolved.')
