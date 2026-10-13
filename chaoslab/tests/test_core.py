from dataclasses import replace
import math
import numpy as np
import pytest
from chaoslab.core import (Config, run, g, allocate, effective_grants,
                          quota_fraction, rc_update, C, _Delay, _rk4, _rhs,
                          _perturbations, SCALE, CAPACITANCE)


def test_piecewise_g_values_and_odd_symmetry():
    x = np.array([-2., -1., 0., 1., 2.])
    np.testing.assert_allclose(g(x), [1.57, 1.02, 0., -1.02, -1.57], atol=1e-15)
    np.testing.assert_array_equal(g(-x), -g(x))


def test_budget_sign_and_local_e_on_random_demands():
    rng = np.random.default_rng(1234)
    ry, rd, re = rng.uniform(-400e-6, 400e-6, (3, 20000))
    fraction = rng.uniform(0, 1, 20000)
    iy, id_, ie = allocate(ry, rd, re, C*fraction, C*(1-fraction))
    assert np.max(np.abs(iy)+np.abs(id_)+np.abs(ie)) <= C+1e-18
    assert np.max(np.abs(ie)) <= 5e-6
    assert np.all(iy*ry >= 0) and np.all(id_*rd >= 0)
    assert np.all(ie*re >= 0)
    assert np.all(ie[re*rd <= 0] == 0)
    assert np.all(np.abs(id_) <= np.abs(rd)+1e-18)


def test_effective_grant_ignores_only_unused_capacity():
    demand = np.array([10., 40., 50.])*1e-6
    a = effective_grants(demand, np.array([20., 40., 30.])*1e-6)
    b = effective_grants(demand, np.array([70., 60., 20.])*1e-6)
    np.testing.assert_array_equal(a[:2], b[:2])
    assert a[2]-b[2] == pytest.approx(10e-6)
    np.testing.assert_allclose(effective_grants(demand, [-1., 1., 1.]), [0., 40e-6, 50e-6])


def test_rc_and_confirmation_analytical_time():
    t_cross = -50e-6*math.log(.3)
    assert t_cross*1e6 == pytest.approx(60.1986402163)
    assert rc_update(0., 1., t_cross, 50e-6) == pytest.approx(.7)
    assert rc_update(.8, 0., 20e-6, 20e-6) == pytest.approx(.8/math.e)


def test_fractional_delay_linear_signal_and_prehistory():
    d = _Delay(10., 1., np.array([3.]))
    for n in range(10):
        d.push(n, np.array([3.+n]))
    np.testing.assert_allclose(d.read(9, 2.5), [9.5])
    np.testing.assert_allclose(d.read(9, 15.), [3.])


def test_analytic_perturbation_cancellation_independent_rhs():
    rng = np.random.default_rng(101)
    x, y = rng.uniform(-1.3, 1.3, (2, 100))
    t = .0375
    p = _perturbations(t)
    ry = .01*(1.015*p[0]*y-p[1]-p[2]*math.sin(.74*t/SCALE))
    rd = .01*p[3]*g(x)
    actual = _rhs(x, y, t, p, ry, rd, np.zeros(100), np.array([3]), False)
    expected = _rhs(x, y, t, None, 0, 0, 0, np.array([3]), True)
    np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-10)


def test_rk4_short_smooth_interval_refines():
    def solve(h):
        x, y = np.array([-.1]), np.array([-.2])
        for n in range(round(100e-6/h)):
            x,y = _rk4(x,y,n*h,h,(0.,0.,0.),np.array([0]),True)
        return np.array([x[0],y[0]])
    ref = solve(.15625e-6)
    errors = [np.linalg.norm(solve(h)-ref) for h in (5e-6,2.5e-6,1.25e-6)]
    assert errors[0]/errors[1] > 10 and errors[1]/errors[2] > 10


@pytest.mark.parametrize("fault", ["healthy", "replay"])
def test_passive_observer_and_refresh_cadence_are_bitwise_invariant(fault):
    base = Config(dt_us=20.,trajectories=2,windows=1,sequence="legacy",
                  profile="coordinator",fallback=False,detector="off",trace_points=30,fault=fault)
    off = run(base)
    snapshots = []
    quota = run(replace(base,detector="quota",monitor_every=137),progress=snapshots.append)
    effective = run(replace(base,detector="effective",monitor_every=311,trace_points=43))
    assert off["validation"]["state_digest"] == quota["validation"]["state_digest"] == effective["validation"]["state_digest"]
    assert off["windows"] == quota["windows"] == effective["windows"]
    assert snapshots[-1]["completed_windows"] == 2
    assert all(w["window_end_s"]-w["window_start_s"] == pytest.approx(.019) for w in off["windows"])
    assert off["timing"]["steps"] == 2500


def test_ensemble_preserves_leading_paths_and_counts_full_windows():
    config = Config(dt_us=25.,trajectories=2,windows=1,sequence="legacy",profile="nominal",trace_points=20)
    first = run(config)
    extended = run(replace(config,trajectories=4))
    assert first["per_trajectory"] == extended["per_trajectory"][:2]
    assert extended["summary"]["total_windows"] == 4
    assert extended["timing"]["aggregate_simulated_seconds"] == pytest.approx(.2)


def test_cancel_returns_no_invented_windows():
    out = run(Config(trajectories=2,windows=20),cancelled=lambda: True)
    assert out["status"] == "cancelled"
    assert out["summary"]["total_windows"] == 0
    assert out["timing"]["steps"] == 0


@pytest.mark.parametrize("kwargs", [{"dt_us": 0}, {"dt_us": float("nan")},
    {"trajectories": 0}, {"windows": -1}, {"detector": "magic"}])
def test_bad_config_rejected(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs).validate()
