from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectionItem

EARTH_RADIUS_KM = 6371.0088


def _point(location: dict | None) -> tuple[float, float] | None:
    if not isinstance(location, dict):
        return None
    try:
        lat = float(location["lat"])
        lon = float(location["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def distance_km(a: dict | None, b: dict | None) -> float | None:
    pa = _point(a)
    pb = _point(b)
    if pa is None or pb is None:
        return None

    lat1, lon1 = map(radians, pa)
    lat2, lon2 = map(radians, pb)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(h), sqrt(1 - h))


def correlate_candidates(anchor: dict, candidates: list[dict], max_distance_km: float = 1.0) -> list[dict]:
    anchor_domain = anchor.get("domain")
    anchor_location = anchor.get("location")
    if not anchor_domain or _point(anchor_location) is None:
        return []

    matches: list[dict] = []
    for candidate in candidates:
        if candidate.get("domain") != anchor_domain:
            continue
        distance = distance_km(anchor_location, candidate.get("location"))
        if distance is None or distance > max_distance_km:
            continue
        matches.append(candidate)

    return sorted(
        matches,
        key=lambda item: (-float(item.get("confidence", 0.0)), str(item.get("id", ""))),
    )


def correlate_observations(db: Session, observation_id: UUID | str) -> list[CollectionItem]:
    observation = db.get(CollectionItem, observation_id)
    if observation is None:
        return []

    candidates = db.scalars(
        select(CollectionItem).where(
            CollectionItem.id != observation.id,
            CollectionItem.domain == observation.domain,
        )
    ).all()

    ranked = correlate_candidates(
        anchor={
            "id": str(observation.id),
            "domain": observation.domain,
            "location": observation.location,
            "confidence": observation.confidence,
        },
        candidates=[
            {
                "id": str(item.id),
                "domain": item.domain,
                "location": item.location,
                "confidence": item.confidence,
                "_model": item,
            }
            for item in candidates
        ],
    )
    return [item["_model"] for item in ranked]
