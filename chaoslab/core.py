"""Fixed-grid, vectorized mathematical surrogate of the Stage 18 MLC model.

The MLC is a continuous ODE. RK4 advances x/y; sampled controllers and exact
zero-order-hold RC updates form an explicitly declared operator splitting.
This is not an emulation of UniversalOpAmp2 or of LTspice's electrical solver.
Observers never participate in the plant's numerical error/step selection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import time
from typing import Callable

import numpy as np

C = 90e-6
CE = 5e-6
CAPACITANCE = 1e-6
SCALE = 100e-6
LEGACY = (0, 0, 1, 0, 2, 0, 3, 1, 1, 2, 1, 3, 2, 2, 3, 3, 0)
CORE_VERSION = "19.1-fixed-rk4-zoh"


@dataclass(frozen=True)
class Config:
    dt_us: float = 5.0
    trajectories: int = 500
    windows: int = 20
    seed: int = 19019
    policy: str = "l2"
    detector: str = "effective"
    fallback: bool = True
    fallback_policy: str = "common"
    fault: str = "healthy"
    profile: str = "coordinator"
    corner: str = "nominal"
    trace_points: int = 1200
    sequence: str = "balanced"
    monitor_every: int = 1000

    def validate(self) -> None:
        choices = {
            "policy": ("l2", "common"),
            "detector": ("quota", "effective", "off"),
            "fallback_policy": ("common", "matched"),
            "fault": ("healthy", "bias", "replay", "dropout", "double", "starve", "stale"),
            "profile": ("ideal", "sensors", "coordinator", "actuator", "nominal", "unlimited"),
            "corner": ("nominal", "plus", "minus"),
            "sequence": ("balanced", "legacy"),
        }
        for field, allowed in choices.items():
            if getattr(self, field) not in allowed:
                raise ValueError(f"{field} must be one of {allowed}")
        if not math.isfinite(self.dt_us) or not .05 <= self.dt_us <= 25:
            raise ValueError("dt_us must be finite and in [0.05, 25]; coarse steps require refinement")
        for field in ("trajectories", "windows", "trace_points", "monitor_every"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{field} must be a positive integer")
        if self.trajectories > 10000 or self.windows > 10000:
            raise ValueError("At most 10000 trajectories or windows per trajectory per run")
        if self.trajectories * self.windows > 2_000_000:
            raise ValueError("Requested window table exceeds the bounded in-memory limit")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if self.estimated_memory_bytes() > 512*1024**2:
            raise ValueError("Estimated in-memory state/result exceeds 512 MiB; reduce trajectories, windows or trace_points")

    def estimated_memory_bytes(self) -> int:
        # Rings plus live vector workspaces, Python result rows and copied traces.
        h = self.dt_us*1e-6
        steps = math.ceil(self.windows*.05/h)
        rings = (math.ceil(500e-6/h)+2*math.ceil(25e-6/h)+12)*self.trajectories*8
        states = 100*self.trajectories*8
        rows = self.windows*self.trajectories*1100
        traces = min(steps+1,self.trace_points+2)*1400
        return int(rings+states+rows+traces+2*1024**2)


def g(x):
    """Piecewise linear MLC nonlinearity; x and g(x) have model-voltage units."""
    return -.55*x + (-1.02+.55)/2*(np.abs(x+1)-np.abs(x-1))


def quota_fraction(request_y, request_d, policy="l2"):
    """Combined signed Y/D requests -> fraction of a single 90-uA capacity."""
    ay, ad = np.abs(request_y), np.abs(request_d)
    total = ay + ad
    common = ay/np.maximum(total, 1e-12)
    if policy == "common":
        return common
    return np.where(total <= C, common, np.clip(.5+(ay-ad)/(2*C), 0., 1.))


def allocate(request_y, request_d, request_e, quota_y, quota_d):
    """Stage 18 signed grants including E's local priority and common budget."""
    quota_y,quota_d = np.clip(quota_y,0,C),np.clip(quota_d,0,C)
    by = np.sign(request_y)*np.minimum(np.abs(request_y), quota_y)
    bd = np.sign(request_d)*np.minimum(np.abs(request_d), quota_d)
    deficit = np.maximum(0., np.abs(request_e)-np.abs(bd)-1e-6)
    enabled = (np.abs(request_d) > np.abs(bd)+1e-6) & (request_e*request_d > 0)
    ee = np.where(enabled, np.sign(request_e)*np.minimum(CE, np.minimum(deficit, np.maximum(0., C-np.abs(bd)))), 0.)
    ey = np.sign(by)*np.minimum(np.abs(by), np.maximum(0., C-np.abs(bd)-np.abs(ee)))
    return ey, bd, ee


def effective_grants(request_abs, quota):
    """Useful unsigned grant, separate from validation of the unmodified quota."""
    return np.minimum(np.abs(request_abs), np.clip(quota, 0., C))


def rc_update(state, source, dt, tau):
    """Exact update for an RC driven by a source held constant over dt."""
    if tau <= 0:
        return np.array(source, dtype=np.float64, copy=True)
    return state + (-math.expm1(-dt/tau))*(source-state)


class _Delay:
    """Finite ring, linear interpolation on the fixed grid, constant prehistory."""
    def __init__(self, maximum_delay, dt, initial):
        self.dt = dt
        self.initial = np.array(initial, dtype=np.float64, copy=True)
        self.data = np.empty((int(math.ceil(maximum_delay/dt))+3,)+self.initial.shape)
        self.data[:] = self.initial

    def push(self, n, value):
        self.data[n % len(self.data)] = value

    def read(self, n, delay):
        coordinate = n-delay/self.dt
        if coordinate <= 0:
            return self.initial
        left = int(math.floor(coordinate))
        weight = coordinate-left
        a = self.data[left % len(self.data)]
        if weight < 1e-12:
            return a
        return a*(1-weight) + self.data[(left+1) % len(self.data)]*weight


def _perturbations(t):
    return np.array((.006*math.sin(2*math.pi*500*t),
                     .009*math.sin(2*math.pi*137*t+math.radians(40)),
                     .007*math.sin(2*math.pi*73*t+math.radians(65)),
                     .008*math.sin(2*math.pi*211*t+math.radians(17))))


def _sequence(config):
    if config.sequence == "legacy":
        return np.resize(np.array(LEGACY, dtype=int), config.windows)
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, 190]))
    return np.concatenate([rng.permutation(4) for _ in range((config.windows+3)//4)])[:config.windows]


def _input_at(t, sequence):
    # Same one-microsecond linear edge as the LTspice PWL. State is continuous.
    k = min(int(math.floor(t/.05+1e-11)), len(sequence)-1)
    code = int(sequence[k])
    a, b = float(code//2), float(code % 2)
    if k and t-k*.05 < 1e-6:
        fraction = max(0., (t-k*.05)/1e-6)
        old = int(sequence[k-1])
        a = old//2 + fraction*(a-old//2)
        b = old % 2 + fraction*(b-old % 2)
    return a, b


def _rhs(x, y, t, p, current_y, current_d, current_e, sequence, nominal):
    a, b = _input_at(t, sequence)
    forcing = math.sin(.74*t/SCALE)
    if nominal:
        dx = (y-g(x))/SCALE
        dy = (-1.015*y-x-.005+.005*(2*a-1+2*b-1)+.11*forcing)/SCALE
    else:
        dx = (y-(1+p[3])*g(x))/SCALE+(current_d+current_e)/CAPACITANCE
        dy = (-1.015*(1+p[0])*y-x-.005+p[1]+.005*(2*a-1+2*b-1)+(.11+p[2])*forcing)/SCALE+current_y/CAPACITANCE
    return dx, dy


def _rk4(x, y, t, h, currents, sequence, nominal):
    cy, cd, ce = currents
    p0 = _perturbations(t) if not nominal else None
    ph = _perturbations(t+h/2) if not nominal else None
    p1 = _perturbations(t+h) if not nominal else None
    k1x,k1y = _rhs(x,y,t,p0,cy,cd,ce,sequence,nominal)
    k2x,k2y = _rhs(x+h/2*k1x,y+h/2*k1y,t+h/2,ph,cy,cd,ce,sequence,nominal)
    k3x,k3y = _rhs(x+h/2*k2x,y+h/2*k2y,t+h/2,ph,cy,cd,ce,sequence,nominal)
    k4x,k4y = _rhs(x+h*k3x,y+h*k3y,t+h,p1,cy,cd,ce,sequence,nominal)
    return x+h/6*(k1x+2*k2x+2*k3x+k4x), y+h/6*(k1y+2*k2y+2*k3y+k4y)


def run(config: Config | dict, progress: Callable | None = None, cancelled: Callable | None = None) -> dict:
    """Run a bounded-memory ensemble; all reported logical windows are complete.

    Callbacks receive copied Python data, never live solver arrays. Their cadence
    and runtime do not enter model time or the numerical update. Cancellation is
    checked at monitor boundaries and returns partial, explicitly labelled data.
    """
    if isinstance(config, dict):
        config = Config(**config)
    config.validate()
    started = time.perf_counter()
    h, count = config.dt_us*1e-6, config.trajectories
    duration = config.windows*.05
    steps = int(math.ceil(duration/h-1e-9))
    sequence = _sequence(config)
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, 191]))
    x = rng.uniform(-.37, .37, count)
    x[0] = -.37
    if count > 1:
        x[1] = .37
    y = np.full(count, -.2)
    initial_x = x.copy()
    plant_nominal = config.profile in ("nominal", "unlimited")
    sensors = config.profile in ("sensors", "coordinator", "actuator")
    coordinated = config.profile in ("coordinator", "actuator")
    actuator = config.profile == "actuator"
    if coordinated:
        lat_coord, tau_coord = (5e-6, 10e-6) if config.policy == "l2" else (20e-6, 50e-6)
    else:
        lat_coord = tau_coord = 0.
    # These are absolute Stage 18 corner settings, not additions to nominal.
    ref_extra, ref_tol, noise, drift, clock_offset = {
        "nominal": (2e-6, .05, .5e-6, 0., 0.),
        "plus": (5e-6, .20, 1e-6, 25e-6, 10e-6),
        "minus": (-5e-6, -.20, 1e-6, -25e-6, -10e-6),
    }[config.corner]
    # Ideal/sensor-only coordinator ablations have matching ideal references.
    ref_delay = max(0., lat_coord+ref_extra) if coordinated else 0.
    ref_tau = tau_coord*(1+ref_tol) if coordinated else 0.
    errors = np.array((.0002,-.0002,.0002,.00002))
    p0 = _perturbations(0.)
    sensor_initial = p0+errors
    sensor_initial[0] = (1+p0[0])*(1+errors[0])-1
    sensor_delay = _Delay(50e-6, h, sensor_initial)
    sensor_state = np.zeros(4)
    fraction_state = np.full(count, .5)
    reference_state = np.full(count, .5)
    first_request_y = .01*(1.015*p0[0]*y-p0[1]-p0[2]*0.) if not sensors else np.zeros(count)
    first_request_d = .01*p0[3]*g(x) if not sensors else np.zeros(count)
    initial_fraction = quota_fraction(first_request_y, first_request_d, config.policy)
    fraction_delay = _Delay(max(lat_coord,ref_delay), h, initial_fraction)
    reference_delay = _Delay(max(lat_coord,ref_delay), h, initial_fraction)
    message_delay = _Delay(500e-6, h, fraction_state if coordinated else initial_fraction)
    observation = np.zeros((2,count))
    reference = np.zeros((2,count))
    timer = np.zeros(count)
    memory = np.zeros(count)
    command_filter = np.zeros((3,count))
    actuator_state = np.zeros((3,count))
    alarm_time = np.full(count, np.nan)
    alarm_source_time = np.full(count, np.nan)
    detected_time = np.full(count, np.nan)
    fallback_time = np.full(count, np.nan)
    harm_time = np.full(count, np.nan)
    false_alarm = np.zeros(count, dtype=bool)
    boundary_alarm = np.zeros(count, dtype=bool)
    late_alarm = np.zeros(count, dtype=bool)
    alarm_causes = [[] for _ in range(count)]
    alarm_timing = ["none"]*count
    fault_seen = np.zeros(count, dtype=bool)
    window_min = np.full((config.windows,count), np.inf)
    window_max = np.full((config.windows,count), -np.inf)
    completed = np.zeros(config.windows, dtype=bool)
    correct_per_trajectory = np.zeros(count,dtype=int)
    peak_per_trajectory = np.zeros(count)
    residual_y2 = np.zeros(count)
    residual_d2 = np.zeros(count)
    g_tv = np.zeros(count)
    metric_samples = 0
    fractional_over_budget = 0
    max_e = 0.
    trace_keys = ("t_s","x","y","request_y_uA","request_d_uA","current_y_uA","current_d_uA","current_e_uA","quota_y_uA","quota_d_uA","budget_uA","error_uA","timer","alarm","reference","input","grant_y_uA","grant_d_uA","age_us")
    trace = {key: [] for key in trace_keys}
    trace_stride = max(1, int(math.ceil(steps/max(1,config.trace_points-1))))
    last_values = None
    status = "complete"
    steps_done = 0
    quota_guard_count = 0
    age_guard_count = 0
    coherence_count = 0
    reserve_samples = 0
    peak = 0.
    permanent = config.fault in ("replay", "stale")
    fault_start = 0. if permanent else .34335
    fault_end = duration if permanent else .40335
    fault_start_step = int(math.ceil(fault_start/h-1e-9))
    fault_end_step = int(math.ceil(fault_end/h-1e-9))
    blanking_last_step = int(math.floor(.002/h+1e-9))

    def add_trace(t, values):
        cy,cd,ce,ry,rd,qy,qd,gy,gd,budget,err,age,tx,ty,tm,mem = values
        code = int(sequence[min(int(t/.05+1e-10),config.windows-1)])
        values_out = (t,float(tx[0]),float(ty[0]),float(ry[0]*1e6),float(rd[0]*1e6),float(cy[0]*1e6),float(cd[0]*1e6),float(ce[0]*1e6),float(qy[0]*1e6),float(qd[0]*1e6),float(budget[0]*1e6),float(err[0]*1e6),float(tm[0]),bool(mem[0]>.5),int(code==3),code,float(gy[0]*1e6),float(gd[0]*1e6),float(age*1e6))
        for key,value in zip(trace_keys,values_out):
            trace[key].append(value)

    def snapshot():
        # Copies keep UI callbacks from mutating solver state or saved traces.
        return dict(fraction=steps_done/steps,elapsed_s=time.perf_counter()-started,
                    completed_windows=int(completed.sum()*count),
                    correct_windows=int(correct_per_trajectory.sum()),
                    peak_budget_uA=peak*1e6,
                    trace={k:list(v[-200:]) for k,v in trace.items()},
                    steps=steps_done,total_steps=steps,status="running")

    for n in range(steps):
        if n % config.monitor_every == 0:
            if cancelled is not None and cancelled():
                status = "cancelled"
                break
            if progress is not None:
                progress(snapshot())
        t = n*h
        t1 = (n+1)*h
        p = _perturbations(t)
        sine = math.sin(.74*t/SCALE)
        if sensors:
            estimate = sensor_state
        else:
            estimate = p
        ry = .01*(1.015*estimate[0]*y-estimate[1]-estimate[2]*sine)
        rd = .01*estimate[3]*g(x)
        # With the nine symmetric, fault-free E replicas the median is D's estimate.
        re = rd.copy()
        target = quota_fraction(ry,rd,config.policy)
        # Independently recomputed from observable measured demands, not messages.
        ref_target = quota_fraction(ry,rd,config.policy)
        fraction_delay.push(n,target)
        reference_delay.push(n,ref_target)
        frac = fraction_state if coordinated else target
        ref_frac = reference_state if coordinated else ref_target
        message_delay.push(n,frac)
        received = message_delay.read(n,500e-6) if permanent else frac
        msg_y = C*received
        msg_d = C*(1-received)
        active_fault = config.fault != "healthy" and fault_start_step <= n < fault_end_step
        hb = 1.
        if active_fault:
            fault_seen[:] = True
            if config.fault == "bias":
                msg_y = np.minimum(C,msg_y+12e-6)
                msg_d = C-msg_y
            elif config.fault == "starve":
                msg_y = np.zeros(count)
                msg_d = np.full(count,C)
            elif config.fault == "dropout":
                msg_y = np.zeros(count)
                msg_d = np.zeros(count)
                hb = 0.
            elif config.fault == "double":
                msg_y = np.full(count,C)
                msg_d = np.full(count,C)
        basic_invalid = (np.minimum(msg_y,msg_d)<-1e-9) | (msg_y+msg_d>C+1e-9) | (hb<.5)
        timestamp_delay = lat_coord+(500e-6 if config.fault == "stale" else 0.)
        age = t*(1+drift)+clock_offset-max(0.,t-timestamp_delay)
        age_invalid = age>80e-6 or age< -30e-6
        discrepancy = np.abs(observation-reference).sum(axis=0)
        incoherent = discrepancy > 6.5e-6
        monitor_enabled = config.detector != "off"
        reason = (basic_invalid | incoherent | age_invalid) if n>blanking_last_step and monitor_enabled else np.zeros(count,dtype=bool)
        reserve = (memory>.5) & config.fallback & monitor_enabled
        first_fallback = reserve & np.isnan(fallback_time)
        fallback_time[first_fallback] = t
        common = np.abs(ry)/np.maximum(np.abs(ry)+np.abs(rd),1e-12)
        local_fraction = common if config.fallback_policy == "common" else ref_frac
        qy = np.where(reserve,C*local_fraction,np.where(basic_invalid,C/2,np.clip(msg_y,0,C)))
        qd = np.where(reserve,C*(1-local_fraction),np.where(basic_invalid,C/2,np.clip(msg_d,0,C)))
        gy,gd,ge = allocate(ry,rd,re,qy,qd)
        raw_grant_y = effective_grants(ry,msg_y)
        raw_grant_d = effective_grants(rd,msg_d)
        expected_grant_y = np.minimum(np.abs(ry),C*frac)
        expected_grant_d = np.minimum(np.abs(rd),C*(1-frac))
        harmed = (np.abs(raw_grant_y-expected_grant_y)+np.abs(raw_grant_d-expected_grant_d)>1e-9) | basic_invalid
        first_harm = np.isnan(harm_time) & harmed & active_fault
        harm_time[first_harm] = t
        if config.profile == "nominal":
            cy,cd,ce = np.zeros(count),np.zeros(count),np.zeros(count)
        elif config.profile == "unlimited":
            # Metrics report instantaneous analytical correction at grid nodes.
            # RHS cancellation is algebraically exact at every RK substage.
            cy = .01*(1.015*p[0]*y-p[1]-p[2]*sine)
            cd = .01*p[3]*g(x)
            ce = np.zeros(count)
        elif actuator:
            cy,cd,ce = actuator_state
            total = np.abs(cy)+np.abs(cd)+np.abs(ce)
            gain = np.minimum(1., C/np.maximum(total,1e-12))
            cy,cd,ce = cy*gain,cd*gain,ce*gain
        else:
            cy,cd,ce = gy,gd,ge
        budget = np.abs(cy)+np.abs(cd)+np.abs(ce)
        peak_per_trajectory = np.maximum(peak_per_trajectory,budget)
        peak = max(peak,float(budget.max()))
        max_e = max(max_e,float(np.abs(ce).max()))
        fractional_over_budget += int(np.count_nonzero(budget>C+1e-15))
        quota_guard_count += int(np.count_nonzero(basic_invalid))
        age_guard_count += count*int(age_invalid)
        coherence_count += int(np.count_nonzero(incoherent))
        reserve_samples += int(np.count_nonzero(reserve))
        true_ry = .01*(1.015*p[0]*y-p[1]-p[2]*sine)
        true_rd = .01*p[3]*g(x)
        if t >= .03:
            residual_y2 += (true_ry-cy)**2 if config.profile != "nominal" else 0.
            residual_d2 += (true_rd-cd-ce)**2 if config.profile != "nominal" else 0.
            metric_samples += 1
        if n % trace_stride == 0:
            add_trace(t,(cy,cd,ce,ry,rd,qy,qd,gy,gd,budget,discrepancy,age,x,y,timer,memory))
        # Observers receive no truth/expected AND or fault-code information.
        qref_y,qref_d = C*ref_frac,C*(1-ref_frac)
        obs_y = msg_y+.5e-6+noise*math.sin(2*math.pi*13007*t)
        obs_d = msg_d-.5e-6+noise*math.sin(2*math.pi*17011*t+.7)
        if config.detector == "effective":
            obs_y = effective_grants(ry,obs_y)
            obs_d = effective_grants(rd,obs_d)
            qref_y = effective_grants(ry,qref_y)
            qref_d = effective_grants(rd,qref_d)
        observation = rc_update(observation,np.array((obs_y,obs_d)),h,4e-6)
        reference = rc_update(reference,np.array((qref_y,qref_d)),h,4e-6)
        old_trip = timer>.7
        timer = np.where(reason,1-(1-timer)*math.exp(-h/50e-6),timer*math.exp(-h/20e-6))
        trip = timer>.7
        first_alarm = np.isnan(alarm_time) & trip
        alarm_time[first_alarm] = t1
        alarm_source_time[first_alarm] = t
        during_alarm = config.fault!="healthy" and fault_start_step <= n+1 < fault_end_step
        # The timer update uses the reason sampled at t, not at t1. A trip
        # timestamped exactly at injection must not credit a pre-fault reason.
        source_before_fault = n < fault_start_step
        before_or_healthy = config.fault=="healthy" or source_before_fault
        boundary_alarm |= first_alarm & (config.fault!="healthy") & source_before_fault & (n+1>=fault_start_step)
        false_alarm |= first_alarm & before_or_healthy
        late_alarm |= first_alarm & (not before_or_healthy) & (not during_alarm)
        detected = first_alarm & active_fault & during_alarm & (~false_alarm)
        detected_time[detected] = t1
        if np.any(first_alarm):
            timing_label = "healthy" if config.fault=="healthy" else "pre_fault_reason_at_boundary" if source_before_fault and n+1>=fault_start_step else "pre_fault" if source_before_fault else "during_fault" if during_alarm else "after_fault"
            for j in np.flatnonzero(first_alarm):
                alarm_timing[j] = timing_label
                alarm_causes[j] = (["heartbeat_range_sum"] if basic_invalid[j] else []) + (["coherence"] if incoherent[j] else []) + (["age"] if age_invalid else [])
                if not alarm_causes[j]:
                    alarm_causes[j] = ["confirmation_memory"]
        # Cmem=1nF/Bmem=1kOhm; negligible 1000-s leakage replaced by latch retention.
        memory = np.where(old_trip,1-(1-memory)*math.exp(-h/1e-6),memory)
        if sensors:
            sample = p+errors
            sample[0] = (1+p[0])*(1+errors[0])-1
            sensor_delay.push(n,sample)
            sensor_state = rc_update(sensor_state,sensor_delay.read(n,50e-6),h,100e-6)
        if coordinated:
            fraction_state = rc_update(fraction_state,fraction_delay.read(n,lat_coord),h,tau_coord)
            reference_state = rc_update(reference_state,reference_delay.read(n,ref_delay),h,ref_tau)
        if actuator:
            actuator_state = rc_update(actuator_state,command_filter,h,1/(2*math.pi*2e6))
            command_filter = rc_update(command_filter,np.array((gy,gd,ge)),h,2e-6)
        xn,yn = _rk4(x,y,t,h,(cy,cd,ce),sequence,plant_nominal)
        if not np.all(np.isfinite(xn)) or not np.all(np.isfinite(yn)):
            raise FloatingPointError(f"Nonfinite plant state at fixed step {n}; reduce dt_us")
        if t1 > .03:
            # Same 30-ms exclusion used for Stage 18 residual/variation metrics.
            # If the fixed grid straddles the boundary, interpolate g there.
            included_fraction = min(1.,(t1-.03)/h)
            g_tv += np.abs(g(xn)-g(x))*included_fraction
        w = min(int(math.floor(t/.05+1e-10)),config.windows-1)
        left,right = w*.05+.03,w*.05+.049
        if t1 >= left and t <= right:
            alpha = max(0.,(left-t)/h)
            beta = min(1.,(right-t)/h)
            xl = x+(xn-x)*alpha
            xr = x+(xn-x)*beta
            window_min[w] = np.minimum(window_min[w],np.minimum(xl,xr))
            window_max[w] = np.maximum(window_max[w],np.maximum(xl,xr))
            if t1 >= right and not completed[w]:
                completed[w] = True
                correct_per_trajectory += (window_min[w]>0) if sequence[w]==3 else (window_max[w]<0)
        x,y = xn,yn
        steps_done = n+1
        last_values = (cy,cd,ce,ry,rd,qy,qd,gy,gd,budget,discrepancy,age,x,y,timer,memory)
    if last_values is not None and (not trace["t_s"] or trace["t_s"][-1]<steps_done*h):
        add_trace(steps_done*h,last_values)
    elapsed = time.perf_counter()-started
    rows = []
    for w in np.flatnonzero(completed):
        expected = int(sequence[w]==3)
        for j in range(count):
            lo,hi = float(window_min[w,j]),float(window_max[w,j])
            margin = lo if expected else -hi
            rows.append(dict(trajectory=j,window=int(w),input=int(sequence[w]),expected=expected,
                             min=lo,max=hi,margin=margin,correct=bool(margin>0),
                             window_start_s=float(w*.05+.03),window_end_s=float(w*.05+.049)))
    sample_total = max(1,steps_done*count)
    total_duration = steps_done*h
    alarms = np.isfinite(alarm_time)
    detects = np.isfinite(detected_time)
    def optional_us(value):
        return float(value*1e6) if np.isfinite(value) else None
    per_trajectory = []
    for j in range(count):
        per_trajectory.append(dict(trajectory=j,initial_x=float(initial_x[j]),initial_y=-.2,
            final_x=float(x[j]),final_y=float(y[j]),total_windows=int(completed.sum()),
            correct_windows=int(correct_per_trajectory[j]),alarm=bool(alarms[j]),
            false_alarm=bool(false_alarm[j]),detected_fault=bool(detects[j]),
            alarm_boundary_before_fault=bool(boundary_alarm[j]),
            alarm_after_fault=bool(late_alarm[j]),alarm_timing=alarm_timing[j],alarm_causes=alarm_causes[j],
            fault_injected=bool(fault_seen[j]),alarm_time_us=optional_us(alarm_time[j]),
            alarm_source_time_us=optional_us(alarm_source_time[j]),
            fallback_time_us=optional_us(fallback_time[j]),
            harm_start_us=optional_us(harm_time[j]),
            detection_latency_us=optional_us(detected_time[j]-fault_start),
            latency_from_harm_us=optional_us(detected_time[j]-harm_time[j]) if np.isfinite(harm_time[j]) else None,
            peak_current_uA=float(peak_per_trajectory[j]*1e6),
            residual_y_rms_uA=float(math.sqrt(residual_y2[j]/max(1,metric_samples))*1e6),
            residual_d_rms_uA=float(math.sqrt(residual_d2[j]/max(1,metric_samples))*1e6),
            g_total_variation_per_s=float(g_tv[j]/max(h,total_duration-.03))))
    summary = dict(total_windows=len(rows),correct_windows=int(correct_per_trajectory.sum()),
        planned_windows=count*config.windows,correct_fraction=float(correct_per_trajectory.sum()/len(rows)) if rows else None,
        alarm_trajectories=int(alarms.sum()),alarms=int(alarms.sum()),
        false_alarm_trajectories=int(false_alarm.sum()),detected_fault_trajectories=int(detects.sum()),
        alarms_after_fault_trajectories=int(late_alarm.sum()),
        alarms_boundary_before_fault_trajectories=int(boundary_alarm.sum()),
        fault_trajectories=int(fault_seen.sum()),peak_current_uA=peak*1e6,peak_budget_uA=peak*1e6,
        peak_e_uA=max_e*1e6,
        residual_y_rms_uA=float(np.sqrt(residual_y2.sum()/max(1,metric_samples*count))*1e6),
        residual_d_rms_uA=float(np.sqrt(residual_d2.sum()/max(1,metric_samples*count))*1e6),
        g_total_variation_per_s=float(g_tv.mean()/max(h,total_duration-.03)),
        quota_guard_fraction=quota_guard_count/sample_total,age_guard_fraction=age_guard_count/sample_total,
        incoherent_fraction=coherence_count/sample_total,reserve_fraction=reserve_samples/sample_total,
        budget_exceedance_fraction=fractional_over_budget/sample_total,
        alarm_times_us=[optional_us(v) for v in alarm_time],harm_start_us=[optional_us(v) for v in harm_time],
        fallback_times_us=[optional_us(v) for v in fallback_time])
    warnings = []
    if config.dt_us>1.25:
        warnings.append("Passo exploratorio grosso: refinar h, h/2 e h/4 antes de conclusoes quantitativas.")
    if actuator:
        warnings.append("Lag de atuador e projecao de corrente sao substitutos matematicos, sem validacao fisica de banda/overshoot.")
    if config.corner != "nominal" and duration>1.5:
        warnings.append("Relogio sem ressincronizacao pode ultrapassar os limites de idade em funcionamento continuo.")
    if config.profile == "unlimited":
        warnings.append("Ablacao ilimitada deliberadamente nao respeita o orcamento de 90 uA.")
    state_hash = hashlib.sha256()
    for state in (x,y,sensor_state,fraction_state,command_filter,actuator_state):
        state_hash.update(np.asarray(state,dtype=np.float64).tobytes())
    result = dict(status=status,config=asdict(config),summary=summary,per_trajectory=per_trajectory,
        windows=rows,trace=trace,
        timing=dict(elapsed_s=elapsed,steps=steps_done,planned_steps=steps,
                    simulated_seconds_per_trajectory=total_duration,
                    aggregate_simulated_seconds=total_duration*count,
                    trajectory_updates=steps_done*count,
                    steps_per_second=steps_done/max(elapsed,1e-12)),
        validation=dict(core_version=CORE_VERSION,fixed_step=True,dt_us=config.dt_us,
            observers_change_step=False,physical_hardware_model=False,
            budget_applies=config.profile not in ("unlimited",),
            budget_ok=bool(peak<=C+1e-15) if config.profile!="unlimited" else None,
            complete_windows_only=True,window_sampling="fixed-grid nodes and linear endpoint interpolation; extrema between nodes unresolved",
            final_state_sha256=hashlib.sha256(np.column_stack((x,y)).tobytes()).hexdigest(),
            state_digest=state_hash.hexdigest(),
            estimated_memory_bytes=config.estimated_memory_bytes(),
            input_sequence=sequence.tolist(),warnings=warnings,
            assumptions=[
                "MLC ODE advanced by RK4; fixed step t=n*h, no adaptive error controller.",
                "Controls are sampled at the left endpoint and held through the RK4 plant step; RC blocks use exact ZOH updates. This operator splitting is not globally fourth order.",
                "Cascaded controller/observer stages update explicitly from their previous states; refine the timestep to quantify sampling/splitting delay.",
                "No state reset between 50-ms blocks within each trajectory. Total windows counts an ensemble, not a single 500-s path.",
                "Initial x: first -0.37, second +0.37, remaining seeded uniform [-0.37,0.37]; initial y=-0.2. Shared deterministic perturbation phases and input sequence.",
                "Balanced sequence uses seeded permutations of the four inputs; legacy repeats the Stage 18 17-block sequence. PWL edges last 1 us.",
                "Fractional delays use linear ring-buffer interpolation and constant t=0 prehistory; timestamp prehistory is zero.",
                "Nine fault-free symmetric E replicas have exactly the same median as D's estimate; this simplification does not validate sensor redundancy or common-cause failures.",
                "Effective-grant detector clips min(abs(request),quota) BEFORE the symmetric 4-us RC; raw heartbeat/range/sum/age guards remain in parallel.",
                "V2 confirmation: charge 50 us, discharge 20 us, threshold 0.7, blanking 2 ms; memory RC 1 us retained without negligible 1000-s leakage. alarm_time is confirmation trip; fallback_time is first actual selection of retained local quotas.",
                "Fallback common: instantaneous proportional policy. Fallback matched: independent reference policy and existing reference delay/RC/tolerance settings, without fault metadata; quotas remain complementary.",
                "False alarms mean first trips in healthy runs or before injection. A first trip after fault removal is reported separately as a late alarm, not automatically labelled false.",
                "Alarm causality uses the reason sampled at the left endpoint: a trip at the injection boundary caused by the preceding healthy interval is a pre-fault alarm, never a detection. alarm_source_time_us records that endpoint.",
                "Residual RMS and total variation of g exclude the first 30 ms; g variation is normalized by simulated duration minus 30 ms, interpolating a straddled boundary.",
                "Profiles are cumulative ideal/sensors/coordinator/actuator. Nominal has no perturbations/correction; unlimited analytically cancels perturbations at every RK stage, so both share the exact nominal RHS.",
                "Actuator profile: command RC 2 us, first-order lag 1/(2pi*2MHz), shared algebraic projection at 90 uA; no op-amp, shunt, thermal, parasitic, or PCB model.",
                "Temporary faults operate 343.35-403.35 ms; replay/stale start at zero. starve=0/90, bias=+12uA toward Y, stale=500us old value and stamp, replay=old value/fresh stamp.",
                "Passive observer independence is numerical by construction; fixed steps still require convergence and do not establish that recovery failure is exclusively equation or hardware.",
            ]))
    if progress is not None:
        final_snapshot = snapshot()
        final_snapshot["status"] = status
        progress(final_snapshot)
    return result
