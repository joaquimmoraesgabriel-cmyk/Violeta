"""Evidence-aware window investigation without inventing channels or causes."""
from __future__ import annotations
import math
import numpy as np

CHANNELS=('request_y_uA','request_d_uA','quota_y_uA','quota_d_uA','grant_y_uA','grant_d_uA',
          'current_y_uA','current_d_uA','current_e_uA','x','y','error_uA','timer','trip','alarm','reserve')


def investigate_window(result,trajectory,window):
    if not isinstance(trajectory,int) or not isinstance(window,int):raise ValueError('Use integer trajectory/window')
    matches=[r for r in result['windows'] if r['trajectory']==trajectory and r['window']==window]
    if len(matches)!=1:raise ValueError('Requested logical window is missing or duplicated')
    row=matches[0]
    paths=[r for r in result['per_trajectory'] if r['trajectory']==trajectory]
    if len(paths)!=1:raise ValueError('Requested trajectory metadata is missing or duplicated')
    path=paths[0]
    start,end=window*.05,(window+1)*.05
    events=[]
    for field,label in (('harm_start_us','first_grant_divergence_or_invalid_message'),
                        ('alarm_source_time_us','sample_causing_first_alarm'),
                        ('alarm_time_us','first_confirmation_trip'),('fallback_time_us','first_reserve_selection')):
        value=path.get(field)
        if value is not None:
            if not math.isfinite(value):raise ValueError('Nonfinite event time')
            events.append(dict(event=label,time_us=value,in_selected_window=start*1e6<=value<=end*1e6,
                               source='per_trajectory.'+field))
    trace=result.get('trace',{});owner=result.get('validation',{}).get('trace_trajectory',0)
    captured={};missing=list(CHANNELS);reason=None;coverage=False
    if owner!=trajectory:reason='The saved trace belongs to another trajectory; verified replay is required.'
    elif len(trace.get('t_s',[]))<2:reason='No usable saved trace; verified replay is required.'
    else:
        times=np.asarray(trace['t_s'],dtype=float)
        if not np.isfinite(times).all() or np.any(np.diff(times)<=0):raise ValueError('Invalid trace timestamps')
        mask=(times>=start-1e-12)&(times<=end+1e-12)
        captured['t_s']=times[mask].tolist()
        for name in CHANNELS:
            if name in trace:
                values=np.asarray(trace[name])
                if len(values)!=len(times) or not np.isfinite(values.astype(float)).all():raise ValueError('Invalid channel: '+name)
                captured[name]=values[mask].tolist()
        missing=[c for c in CHANNELS if c not in captured]
        coverage=times[0]<=row['window_start_s'] and times[-1]>=row['window_end_s'] and int(mask.sum())>=2
        if not coverage:reason='The saved trace does not cover the evaluation interval; verified replay is required.'
    return dict(trajectory=trajectory,window=window,logical_window=dict(row),
        evaluation_interval_s=[row['window_start_s'],row['window_end_s']],
        trace_trajectory=owner,trace=captured,trace_covers_evaluation=coverage,
        needs_replay=not coverage,reason=reason,missing_channels=missing,events=events,
        alarm_causes=path.get('alarm_causes',[]),
        distinction='alarm_time is confirmation trip; fallback_time is first selected reserve. Saved alarm channel is retained memory, not the trip timestamp.',
        interpretation='Window metrics use the original integrator samples. Saved trace is decimated; events from metadata are first events of the whole trajectory. Temporal order alone does not establish causality. Grant divergence can include beneficial increases.')
