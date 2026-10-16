from copy import deepcopy
import pytest
from chaoslab.diagnostics import investigate_window


def fixture():
    return dict(windows=[dict(trajectory=1,window=0,input=3,expected=1,min=-1,max=1,margin=-1,
                correct=False,window_start_s=.03,window_end_s=.049)],
        per_trajectory=[dict(trajectory=1,alarm_time_us=32000,fallback_time_us=32005,
            harm_start_us=31000,alarm_causes=['coherence'])],validation=dict(trace_trajectory=0),
        trace=dict(t_s=[0,.03,.04,.05],x=[-1,-1,1,1],alarm=[False,False,True,True]))


def test_wrong_trace_never_attributed_to_selected_trajectory():
    out=investigate_window(fixture(),1,0)
    assert out['needs_replay'] and out['trace']=={}
    assert out['logical_window']['margin']==-1
    assert out['events'][1]['event']=='first_confirmation_trip'


def test_missing_channels_and_exact_metadata_events_are_distinguished():
    r=fixture();r['validation']['trace_trajectory']=1
    out=investigate_window(r,1,0)
    assert not out['needs_replay'] and out['trace']['x']==[-1,-1,1,1]
    assert 'reserve' in out['missing_channels'] and 'reserve' not in out['trace']
    assert [e['time_us'] for e in out['events']]==[31000,32000,32005]


def test_insufficient_coverage_and_bad_selection():
    r=fixture();r['validation']['trace_trajectory']=1;r['trace']={'t_s':[0,.01],'x':[0,0]}
    assert investigate_window(r,1,0)['needs_replay']
    with pytest.raises(ValueError):investigate_window(r,0,0)
    r['trace']['t_s']=[0,0]
    with pytest.raises(ValueError):investigate_window(r,1,0)
