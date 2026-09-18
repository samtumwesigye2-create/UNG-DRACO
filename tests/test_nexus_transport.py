from app.services.nexus_transport import build_observation_event

def test_observation_envelope_contract():
    event=build_observation_event(
        observation_id="obs-test-001",
        source_type="rgb_noir",
        domain="imagery",
        platform="DRACO-G1-001",
        location={"site":"bench"},
        confidence=0.91,
    )
    assert event["source_system"]=="UNG-DRACO"
    assert event["target_system"]=="UNG-PULSAR"
    assert event["message_type"]=="observation.created"
    assert event["correlation_id"]=="obs-test-001"
    assert event["trace_id"]==event["message_id"]
    assert event["payload"]["event_id"]==event["message_id"]
    assert event["payload"]["observation_id"]=="obs-test-001"
    assert event["payload"]["device_id"]=="DRACO-G1-001"
    assert event["payload"]["sensor_id"]=="rgb_noir"
    assert event["payload"]["confidence"]==0.91
