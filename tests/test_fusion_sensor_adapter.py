import math
import pytest
from app.services.fusion_sensor_adapter import normalize_measurement, ingest_measurement
from app.services.fusion_field import FusionFieldEngine

def test_normalizes_2d_sensor_measurement():
    m=normalize_measurement("S1",[10,20],.8,.9,"2026-09-24T23:00:00+00:00",{"source":"test"})
    assert m.position == [10.0,20.0,0.0]
    assert m.sensor_id == "S1"
    assert m.metadata["source"] == "test"

@pytest.mark.parametrize("sensor_id",["S0","S4","camera"])
def test_rejects_unknown_sensor_slots(sensor_id):
    with pytest.raises(ValueError): normalize_measurement(sensor_id,[0,0],.5)

def test_rejects_nonfinite_coordinates():
    with pytest.raises(ValueError): normalize_measurement("S1",[math.inf,0],.5)

def test_rejects_invalid_timestamp():
    with pytest.raises(ValueError): normalize_measurement("S1",[0,0],.5,timestamp="not-a-time")

def test_engine_fuses_three_sensor_measurements():
    e=FusionFieldEngine()
    e.ingest("S1",[0,0],.9,.9)
    e.ingest("S2",[2,0],.9,.9)
    state=e.ingest("S3",[1,2],.9,.9)
    assert state["status"] == "fused"
    assert set(state["sensors"]) == {"S1","S2","S3"}
    assert len(state["provenance"]) == 3
    assert state["envelope_radius"] >= 0
