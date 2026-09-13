from app.services.correlation import correlate_candidates


def test_correlates_same_domain_nearby_observations():
    matches = correlate_candidates(
        anchor={"domain": "air", "location": {"lat": 0.3136, "lon": 32.5811}, "confidence": 0.82},
        candidates=[
            {"id": "a", "domain": "air", "location": {"lat": 0.3140, "lon": 32.5815}, "confidence": 0.75},
            {"id": "b", "domain": "ground", "location": {"lat": 0.3140, "lon": 32.5815}, "confidence": 0.91},
        ],
    )
    assert [item["id"] for item in matches] == ["a"]


def test_correlation_orders_by_confidence_then_id():
    matches = correlate_candidates(
        anchor={"domain": "air", "location": {"lat": 0.3136, "lon": 32.5811}, "confidence": 0.82},
        candidates=[
            {"id": "b", "domain": "air", "location": {"lat": 0.3137, "lon": 32.5812}, "confidence": 0.75},
            {"id": "a", "domain": "air", "location": {"lat": 0.3138, "lon": 32.5813}, "confidence": 0.75},
            {"id": "c", "domain": "air", "location": {"lat": 0.3139, "lon": 32.5814}, "confidence": 0.90},
        ],
    )
    assert [item["id"] for item in matches] == ["c", "a", "b"]
