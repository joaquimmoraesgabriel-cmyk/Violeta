"""Bounded, reproducible experiment plans; no Streamlit or hidden model edits.

Numerical refinement holds the request sampling clock fixed. Paired statistics
use window identities; identical totals alone never certify convergence.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np

from chaoslab.engine import Config, run

DISPLAY_FIELDS = {'trace_points','trace_trajectory','trace_start_s','trace_end_s','monitor_every'}


def config_diff(a: dict, b: dict) -> dict:
    return {k: [a.get(k),b.get(k)] for k in sorted(set(a)|set(b))
            if a.get(k)!=b.get(k) and k not in DISPLAY_FIELDS}


def compare_results(a: dict, b: dict, *, allowed_differences=()) -> dict:
    """Require identical experimental subjects/inputs before pairing windows."""
    if a.get('status')!='complete' or b.get('status')!='complete':
        raise ValueError('Only completed cases can be compared')
    differences = config_diff(a['config'],b['config'])
    unexpected = set(differences)-set(allowed_differences)
    if unexpected:
        raise ValueError('Comparison changes undeclared conditions: '+', '.join(sorted(unexpected)))
    if a['validation']['input_sequence'] != b['validation']['input_sequence']:
        raise ValueError('Different inputs cannot be paired')
    ia=[(v['trajectory'],v['initial_x'],v['initial_y']) for v in a['per_trajectory']]
    ib=[(v['trajectory'],v['initial_x'],v['initial_y']) for v in b['per_trajectory']]
    if ia!=ib: raise ValueError('Different initial states cannot be paired')
    def keyed(result):
        rows={(r['trajectory'],r['window']):r for r in result['windows']}
        if len(rows)!=len(result['windows']): raise ValueError('Duplicate windows')
        return rows
    ra,rb=keyed(a),keyed(b)
    if ra.keys()!=rb.keys(): raise ValueError('Different completed windows cannot be paired')
    changes=[]
    for key,x in sorted(ra.items()):
        y=rb[key]
        if (x['input'],x['expected'],x['window_start_s'],x['window_end_s'])!=(y['input'],y['expected'],y['window_start_s'],y['window_end_s']):
            raise ValueError('Window protocol mismatch')
        changes.append(dict(trajectory=key[0],window=key[1],baseline_correct=x['correct'],
            candidate_correct=y['correct'],baseline_margin=x['margin'],candidate_margin=y['margin'],
            margin_delta=y['margin']-x['margin'],changed=x['correct']!=y['correct']))
    recovered=sum(not r['baseline_correct'] and r['candidate_correct'] for r in changes)
    regressed=sum(r['baseline_correct'] and not r['candidate_correct'] for r in changes)
    residuals={k: [a['summary'][k],b['summary'][k]] for k in
               ('residual_y_rms_uA','residual_d_rms_uA','g_total_variation_per_s','peak_current_uA','false_alarm_trajectories')}
    return dict(windows=len(changes),baseline_correct=sum(r['baseline_correct'] for r in changes),
        candidate_correct=sum(r['candidate_correct'] for r in changes),recovered=recovered,regressed=regressed,
        net=recovered-regressed,discordant=recovered+regressed,window_pairs=changes,
        identical_final_state=a['validation']['final_state_sha256']==b['validation']['final_state_sha256'],
        condition_differences=differences,metrics=residuals,
        interpretation='Paired descriptive comparison; convergence and causal generalization require additional evidence.')


def compare_traces(a: dict, b: dict, end_s: float | None = None) -> dict:
    """Interpolation only on overlapping recorded timestamps, never extrapolate."""
    ta,tb=np.asarray(a['trace']['t_s']),np.asarray(b['trace']['t_s'])
    if len(ta)<2 or len(tb)<2: return dict(available=False,reason='Insufficient trace samples')
    if a['validation'].get('trace_trajectory',0)!=b['validation'].get('trace_trajectory',0):
        raise ValueError('Trace trajectories differ')
    lo=max(ta[0],tb[0]); hi=min(ta[-1],tb[-1],end_s if end_s is not None else math.inf)
    grid=ta[(ta>=lo)&(ta<=hi)]
    if len(grid)<2: return dict(available=False,reason='No recorded time overlap')
    channels={}
    for key in ('x','y','current_y_uA','current_d_uA','current_e_uA'):
        delta=np.interp(grid,tb,b['trace'][key])-np.interp(grid,ta,a['trace'][key])
        channels[key]=dict(rms=float(np.sqrt(np.mean(delta**2))),max_abs=float(np.max(np.abs(delta))))
    return dict(available=True,interval_s=[float(grid[0]),float(grid[-1])],samples=len(grid),channels=channels,
                interpretation='Recorded traces with interpolation; this is not a full-resolution error bound.')


def convergence_plan(base: Config, steps=(5.,2.5,1.25)) -> list[tuple[str,Config]]:
    steps=tuple(float(h) for h in steps)
    if not 2<=len(steps)<=6 or any(a<=b for a,b in zip(steps,steps[1:])):
        raise ValueError('Use 2..6 strictly decreasing integration steps')
    sample=base.sample_period_us or steps[0]
    result=[]
    for h in steps:
        cfg=replace(base,dt_us=h,sample_period_us=sample)
        cfg.validate()
        result.append((f'h_{h:g}us',cfg))
    return result


def equivalent_plan(base: Config, mode='policy') -> list[tuple[str,Config]]:
    """Hold explicit coordinator timing fixed; budget ablation uses two ZOH controls."""
    timing=dict(coordinator_delay_us=base.coordinator_delay_us if base.coordinator_delay_us is not None else 5.,
                coordinator_tau_us=base.coordinator_tau_us if base.coordinator_tau_us is not None else 10.,
                sample_period_us=base.sample_period_us or base.dt_us)
    fixed=replace(base,**timing)
    if mode=='policy':
        if fixed.profile not in ('coordinator','actuator'):
            raise ValueError('Policy comparison requires coordinator/actuator profile')
        cases=[('l2_matched_timing',replace(fixed,policy='l2')),
               ('common_matched_timing',replace(fixed,policy='common'))]
    elif mode=='budget':
        # Uncapped sampled profile has ideal sensing; match those conditions exactly.
        fixed=replace(fixed,detector='off',fallback=False,fault='healthy',additional_faults=())
        cases=[('limited_sampled',replace(fixed,profile='ideal')),
               ('unlimited_sampled',replace(fixed,profile='unlimited_sampled'))]
    else: raise ValueError('mode must be policy or budget')
    for _,cfg in cases: cfg.validate()
    return cases


ROBUST_RANGES={
    'coordinator_delay_us':(2.,10.),'coordinator_tau_us':(8.,12.),
    'reference_extra_us':(-5.,5.),'reference_tolerance':(-.2,.2),
    'observation_noise_uA':(0.,1.),'clock_drift_ppm':(-25.,25.),
    'clock_offset_us':(-10.,10.),'sensor_error_scale':(.8,1.2),
    'noise_phase':(-math.pi,math.pi)}


def robustness_plan(base: Config, scenarios=4, seed=20191, ranges=None, new_inputs=True,
                    new_initial_states=True, combined_faults=()) -> list[tuple[str,Config]]:
    if not isinstance(scenarios,int) or not 1<=scenarios<=12:
        raise ValueError('Use 1..12 paired robustness scenarios')
    if not isinstance(seed,int) or seed<0: raise ValueError('Seed must be a nonnegative integer')
    ranges=ROBUST_RANGES if ranges is None else ranges
    if not isinstance(ranges,dict): raise ValueError('Robustness ranges must be a JSON object')
    if set(ranges)-set(ROBUST_RANGES): raise ValueError('Unsupported robustness parameter')
    rng=np.random.default_rng(seed); cases=[]
    for n in range(scenarios):
        changes={}
        for key,bounds in sorted(ranges.items()):
            if len(bounds)!=2 or not all(math.isfinite(x) for x in bounds) or bounds[0]>bounds[1]:
                raise ValueError('Invalid range: '+key)
            changes[key]=float(rng.uniform(*bounds))
        if new_inputs:
            changes.update(seed=int(rng.integers(0,2**31-1)),sequence='balanced',input_codes=())
        if new_initial_states:
            changes['initial_x']=tuple(float(x) for x in rng.uniform(-.37,.37,base.trajectories))
        cfg=replace(base,additional_faults=tuple(combined_faults),**changes)
        cfg.validate()
        for detector in ('quota','effective'):
            cases.append((f'scenario_{n:02d}_{detector}',replace(cfg,detector=detector)))
    return cases


def run_plan(cases: list[tuple[str,Config]], kind: str, progress: Callable | None = None,
             cancelled: Callable | None = None) -> dict:
    """Sequential plan with bounded state and cooperative cancellation."""
    if kind not in ('convergence','equivalent','robustness'):
        raise ValueError('Unknown workbench kind')
    if not 1<=len(cases)<=24 or len({n for n,_ in cases})!=len(cases):
        raise ValueError('Use 1..24 uniquely named cases')
    for _,cfg in cases: cfg.validate()
    if sum(c.estimated_memory_bytes() for _,c in cases)>768*1024**2:
        raise ValueError('Plan exceeds conservative 768 MiB memory estimate')
    records=[];results=[];status='complete'
    for i,(name,cfg) in enumerate(cases):
        if cancelled and cancelled(): status='cancelled';break
        def update(s):
            if progress: progress(dict(s,case=name,case_index=i,total_cases=len(cases),
                                        overall_fraction=(i+s['fraction'])/len(cases)))
        result=run(cfg,progress=update,cancelled=cancelled)
        results.append(result)
        records.append(dict(name=name,status=result['status'],summary=result['summary']))
        if result['status']!='complete': status=result['status'];break
    comparisons=[]
    if status=='complete':
        pairs=list(zip(range(len(results)-1),range(1,len(results)))) if kind=='convergence' else list(zip(range(0,len(results)-1,2),range(1,len(results),2)))
        allowed={'dt_us'} if kind=='convergence' else {'policy','profile'} if kind=='equivalent' else {'detector'}
        for a,b in pairs:
            paired=compare_results(results[a],results[b],allowed_differences=allowed)
            paired.update(baseline=cases[a][0],candidate=cases[b][0],
                          short_trace=compare_traces(results[a],results[b],end_s=.002))
            comparisons.append(paired)
    plan=[dict(name=name,config=asdict(cfg)) for name,cfg in cases]
    return dict(schema='chaoslab-workbench-v1',kind=kind,status=status,plan=plan,
        plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),
        cases=records,results=results,comparisons=comparisons,
        interpretation='Validation experiment, not a new research-stage conclusion. Robustness ranges are deterministic/seeded scenarios, not measured fabrication distributions.')


def replay_window(result: dict, trajectory: int, window: int, progress=None, cancelled=None) -> dict:
    if not any(r['trajectory']==trajectory and r['window']==window for r in result['windows']):
        raise ValueError('Window is absent from the original result')
    cfg=Config(**result['config'])
    start=window*.05; end=min((window+1)*.05,cfg.duration_s or cfg.windows*.05)
    # Keep the entire original evolution and all initial conditions. Only capture changes.
    cfg=replace(cfg,trace_trajectory=trajectory,trace_start_s=start,trace_end_s=end,trace_points=5000)
    repeated=run(cfg,progress=progress,cancelled=cancelled)
    if repeated['status']=='complete':
        if repeated['validation']['final_state_sha256']!=result['validation']['final_state_sha256'] or repeated['windows']!=result['windows']:
            raise ValueError('Replay differs from original; code/configuration provenance needs review')
        repeated['validation']['replay_verified']=True
    return repeated
