from app.services.correlation import correlate_candidates


def test_correlates_same_domain_nearby_observations():
    matches = correlate_candidates(
        anchor={
            "id": "anchor",
            "domain": "air",
            "location": {"lat": 0.3136, "lon": 32.5811},
            "confidence": 0.82,
        },
        candidates=[
            {
                "id": "a",
                "domain": "air",
                "location": {"lat": 0.3140, "lon": 32.5815},
                "confidence": 0.75,
            },
            {
                "id": "b",
                "domain": "ground",
                "location": {"lat": 0.3140, "lon": 32.5815},
                "confidence": 0.91,
            },
            {
                "id": "c",
                "domain": "air",
                "location": {"lat": 1.0, "lon": 33.0},
                "confidence": 0.99,
            },
        ],
    )

    assert [item["id"] for item in matches] == ["a"]
