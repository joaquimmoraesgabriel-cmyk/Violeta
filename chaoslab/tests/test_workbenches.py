from dataclasses import asdict,replace
import hashlib
from pathlib import Path
import numpy as np
import pytest
from chaoslab import core,engine
from chaoslab.workbenches import (compare_results,compare_traces,convergence_plan,equivalent_plan,
                                  robustness_plan,run_plan,replay_window)


def cfg(**kwargs):
    return engine.Config(**dict(dict(trajectories=2,windows=1,dt_us=10.,duration_s=.0002,
        metrics_warmup_s=0,trace_points=100,detector='off'),**kwargs))


def test_frozen_source_and_default_compatibility():
    assert hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest()=='aacd24fd53246cc1f3f0f258b2c469137064a774c69511b573f24f0ae73d097e'
    c=core.Config(dt_us=25.,trajectories=2,windows=1,trace_points=30)
    a,b=core.run(c),engine.run(engine.Config(**asdict(c)))
    assert a['validation']['state_digest']==b['validation']['state_digest']
    assert a['windows']==b['windows']


def test_unlimited_sampled_is_zoh_and_matches_nonbinding_cap():
    a=engine.run(cfg(profile='ideal',budget_uA=10000,reserve_uA=0,sample_period_us=20))
    b=engine.run(cfg(profile='unlimited_sampled',budget_uA=10000,reserve_uA=0,sample_period_us=20))
    np.testing.assert_allclose(a['trace']['x'],b['trace']['x'],atol=1e-14,rtol=0)
    assert b['trace']['current_y_uA'][0]==b['trace']['current_y_uA'][1]
    assert b['validation']['budget_applies'] is False
    exact=engine.run(cfg(profile='unlimited'))
    assert b['validation']['final_state_sha256']!=exact['validation']['final_state_sha256']


def test_fixed_sampling_and_matched_policy_timing():
    plan=convergence_plan(cfg(dt_us=5),steps=(5,2.5,1.25))
    assert [c.sample_period_us for _,c in plan]==[5,5,5]
    plan=equivalent_plan(cfg())
    assert len(plan)==2 and plan[0][1].coordinator_delay_us==plan[1][1].coordinator_delay_us
    report=run_plan(plan,'equivalent')
    assert set(report['comparisons'][0]['condition_differences'])=={'policy'}
    assert report['results'][0]['validation']['coordinator_tau_us']==report['results'][1]['validation']['coordinator_tau_us']


def test_refinement_improves_short_smooth_nominal_state():
    base=cfg(dt_us=5,profile='nominal',initial_x=(-.1,-.1))
    reference=engine.run(replace(base,dt_us=.3125))
    reference=np.array([reference['per_trajectory'][0][k] for k in ('final_x','final_y')])
    report=run_plan(convergence_plan(base),'convergence')
    errors=[np.linalg.norm(np.array([r['per_trajectory'][0][k] for k in ('final_x','final_y')])-reference) for r in report['results']]
    assert errors[0]>errors[1]>errors[2]


def test_equal_counts_do_not_hide_discordant_windows():
    a=engine.run(cfg())
    import copy
    b=copy.deepcopy(a)
    def row(j,correct): return dict(trajectory=j,window=0,input=0,expected=0,
        window_start_s=.03,window_end_s=.049,margin=1 if correct else -1,correct=correct)
    a['windows']=[row(0,True),row(1,False)]
    b['windows']=[row(0,False),row(1,True)]
    paired=compare_results(a,b)
    assert (paired['net'],paired['recovered'],paired['regressed'],paired['discordant'])==(0,1,1,2)
    b['config']['seed']+=1
    with pytest.raises(ValueError): compare_results(a,b)


def test_robustness_is_reproducible_paired_and_varies_inputs():
    a=robustness_plan(cfg(),scenarios=3,seed=42)
    assert a==robustness_plan(cfg(),scenarios=3,seed=42)
    assert a!=robustness_plan(cfg(),scenarios=3,seed=43)
    for i in range(0,len(a),2):
        x,y=asdict(a[i][1]),asdict(a[i+1][1]);x.pop('detector');y.pop('detector')
        assert x==y
    assert a[0][1].initial_x!=a[2][1].initial_x


def test_combined_fault_and_budget_are_observed():
    r=engine.run(cfg(dt_us=5,duration_s=.003,detector='effective',fault='bias',
        fault_start_s=.0022,fault_end_s=.0029,additional_faults=('dropout',),budget_uA=70,reserve_uA=3))
    assert r['summary']['detected_fault_trajectories']==2
    assert r['summary']['peak_current_uA']<=70+1e-9
    assert r['summary']['peak_e_uA']<=3+1e-9
    assert r['summary']['quota_guard_fraction']>0


def test_trace_selection_does_not_change_simulation():
    a=engine.run(cfg(trace_trajectory=0));b=engine.run(cfg(trace_trajectory=1))
    assert a['validation']['state_digest']==b['validation']['state_digest']
    assert a['trace']['x'][0]!=b['trace']['x'][0]
    with pytest.raises(ValueError): compare_traces(a,b)


def test_replay_preserves_original_and_cancellation_not_complete():
    a=engine.run(cfg(duration_s=None,dt_us=25,trace_points=10))
    r=replay_window(a,1,0)
    assert r['validation']['replay_verified']
    assert r['validation']['trace_trajectory']==1
    cancelled=run_plan(convergence_plan(cfg(dt_us=5)),'convergence',cancelled=lambda:True)
    assert cancelled['status']=='cancelled' and cancelled['comparisons']==[]


@pytest.mark.parametrize('changes',[dict(sample_period_us=11),dict(budget_uA=-1),
    dict(additional_faults=('unknown',)),dict(trace_trajectory=2),dict(input_codes=(4,)),
    dict(duration_s=.000201),dict(reserve_uA=91)])
def test_invalid_advanced_settings(changes):
    with pytest.raises(ValueError): cfg(**changes).validate()


def test_short_horizon_does_not_report_unmeasured_residual_as_zero():
    r=engine.run(cfg(metrics_warmup_s=.03))
    assert r['validation']['metrics_available'] is False
    assert r['summary']['residual_y_rms_uA'] is None
    assert r['summary']['total_windows']==0


def test_units_allow_scientific_notation_and_control_sampling_validation():
    assert engine._us(1e-5)==1e-11
    with pytest.raises(ValueError):cfg(dt_us=.05,sample_period_us=9999.999999).validate()
