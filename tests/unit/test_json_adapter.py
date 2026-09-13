import pytest

from app.adapters.json_source import JSONSourceAdapter


def test_json_adapter_normalizes_live_source_payload():
    adapter = JSONSourceAdapter(source_type="sensor", domain="air")

    observation = adapter.normalize(
        {
            "platform": "field-camera-7",
            "location": {"lat": 0.3476, "lon": 32.5825},
            "content": "vehicle observed",
            "confidence": 0.91,
        }
    )

    assert observation == {
        "source_type": "sensor",
        "domain": "air",
        "platform": "field-camera-7",
        "location": {"lat": 0.3476, "lon": 32.5825},
        "raw_content": "vehicle observed",
        "confidence": 0.91,
    }


def test_json_adapter_rejects_non_object_payloads():
    adapter = JSONSourceAdapter(source_type="sensor", domain="air")

    with pytest.raises(ValueError, match="JSON payload must be an object"):
        adapter.normalize(["invalid"])


def test_json_adapter_rejects_out_of_range_confidence():
    adapter = JSONSourceAdapter(source_type="sensor", domain="air")

    with pytest.raises(ValueError, match="confidence"):
        adapter.normalize({"confidence": 1.5})
