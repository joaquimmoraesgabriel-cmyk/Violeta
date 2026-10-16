from dataclasses import replace
import json
import numpy as np
import pytest
from chaoslab import bridge
from chaoslab.engine import Config,run


def nominal():return Config(profile='nominal',trajectories=2,windows=2,input_codes=(0,3),dt_us=5)


def test_manifest_inputs_units_and_netlist():
    m=bridge.make_manifest(nominal(),trajectory=1)
    assert m['initial']=={'x_V':.37,'y_V':-.2}
    assert m['inputs']['codes']==[0,3]
    assert m['duration_s']==.1 and m['physics']['capacitance_F']==1e-6
    text=bridge.netlist(m)
    assert 'IC=0.37' in text and 'Bx 0 x' in text and 'By 0 y' in text
    assert '.ic V(x)=' in text and ' uic' not in text
    assert '0.050001' in text and '.tran 0 ' in text
    assert len(bridge.bundle_zip(m))>100


def test_export_is_scoped_and_does_not_overwrite(tmp_path,monkeypatch):
    monkeypatch.setattr(bridge,'ROOT',tmp_path);monkeypatch.setattr(bridge,'MIN_FREE_GB',0)
    m=bridge.make_manifest(nominal())
    dest=tmp_path/'chaoslab/bridge_exports/test'
    exported=bridge.export_bundle(m,dest)
    assert json.loads((dest/'manifest.json').read_text())['manifest_sha256']==m['manifest_sha256']
    with pytest.raises(ValueError):bridge.export_bundle(m,dest)
    with pytest.raises(ValueError):bridge.export_bundle(m,tmp_path/'outside')
    m['initial']['x_V']=100
    with pytest.raises(ValueError):bridge.netlist(m)


def test_unsupported_physical_model_refused():
    with pytest.raises(ValueError,match='nominal'):bridge.make_manifest(replace(nominal(),profile='actuator'))


@pytest.mark.parametrize('data',[b'time,V(x),V(y)\n0,1,2\n0.1,2,3',
    'time\tV(x)\tV(y)\n0\t1\t2\n0.1\t2\t3'.encode('utf-16')])
def test_csv_supported_encodings(data):
    out=bridge.import_csv(data)
    assert out['trace']['x']==[1,2] and out['trace']['t_s']==[0,.1]


@pytest.mark.parametrize('data',[b'time,x,y\n0,1,2\n0,nan,3',b'time,x,y\n1,1,2\n0,2,3',
    b'time,x,y\n0,1,2\n0,2,3',b'time,x,y\n0,1,2\n1,2',b'time,x\n0,1\n1,2'])
def test_bad_csv_rejected(data):
    with pytest.raises(ValueError):bridge.import_csv(data)


def test_overlap_without_extrapolation_and_raw_parse():
    a={'t_s':[0.,1.,2.,3.],'x':[0,1,2,3],'y':[0,2,4,6]}
    b={'t_s':[.5,1.5,2.5],'x':[.5,1.5,2.5],'y':[1,3,5]}
    c=bridge.compare(a,b)
    assert c['interval_s']==[1.,2.] and c['channels']['x']['max_abs']==0
    with pytest.raises(ValueError):bridge.compare(a,dict(b,t_s=[4,5,6]))
    header='Title: test\nFlags: real forward\nNo. Variables: 3\nNo. Points: 2\nVariables:\n0 time time\n1 V(x) voltage\n2 V(y) voltage\nBinary:\n'
    arr=np.array([(0.,[1.,2.]),(.1,[3.,4.])],dtype=[('t','<f8'),('v','<f4',(2,))])
    data=header.encode('utf-16-le')+arr.tobytes()
    assert bridge.import_raw(data)['trace']['x']==[1,3]
    with pytest.raises(ValueError):bridge.import_raw(data[:-1])


def test_logic_uses_saved_python_extrema_and_complete_imported_intervals():
    result={'windows':[dict(trajectory=0,window=0,input=0,expected=0,margin=1,correct=True,
                           window_start_s=.03,window_end_s=.049),
                       dict(trajectory=0,window=1,input=3,expected=1,margin=1,correct=True,
                           window_start_s=.08,window_end_s=.099)]}
    imported={'t_s':[0,.03,.04,.049,.05],'x':[-1,-1,1,-1,-1],'y':[0]*5}
    report=bridge.logical_comparison(result,imported)
    assert report['compared']==1 and report['discordant']==1 and report['incomplete_windows']==[1]
