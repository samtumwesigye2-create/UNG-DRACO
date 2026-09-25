from app.api.device import Heartbeat

def test_power_motion_telemetry_is_optional():
    h=Heartbeat(unit_id="draco-1")
    assert h.input_voltage_v is None
    assert h.s1_power_ok is None
    assert h.undervoltage is False

def test_power_motion_telemetry_accepts_valid_values():
    h=Heartbeat(unit_id="draco-1",input_voltage_v=5.1,input_current_a=1.2,input_power_w=6.12,
                battery_percent=82,power_source="battery",s1_power_ok=True,s2_power_ok=True,
                s3_power_ok=False,pan_tilt_power_ok=True)
    assert h.input_voltage_v == 5.1
    assert h.battery_percent == 82
    assert h.s3_power_ok is False

def test_power_motion_telemetry_rejects_invalid_battery_percent():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Heartbeat(unit_id="draco-1",battery_percent=101)
