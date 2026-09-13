from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Track, Watch
from app.services.correlation import distance_km


def _watch_matches(watch: Watch, track: Track) -> tuple[bool, str]:
    if watch.target_type == "domain":
        matched = watch.target.strip().lower() == (track.target_type or "").strip().lower()
        return matched, f"domain={track.target_type}"

    if watch.target_type == "location" and track.location:
        try:
            lat_text, lon_text = [part.strip() for part in watch.target.split(",", 1)]
            target_location = {"lat": float(lat_text), "lon": float(lon_text)}
        except (ValueError, TypeError):
            return False, "invalid watch location"
        distance = distance_km(target_location, track.location)
        if distance is None:
            return False, "track has no valid location"
        return distance <= 1.0, f"distance_km={distance:.3f}"

    return False, "unsupported watch condition"


def evaluate_watches(db: Session, track: Track) -> list[Alert]:
    watches = db.scalars(select(Watch).where(Watch.active.is_(True))).all()
    created: list[Alert] = []
    for watch in watches:
        matched, reason = _watch_matches(watch, track)
        if not matched:
            continue
        existing = db.scalar(
            select(Alert).where(
                Alert.watch_id == watch.id,
                Alert.track_id == track.id,
                Alert.acknowledged.is_(False),
            )
        )
        if existing is not None:
            continue
        alert = Alert(
            watch_id=watch.id,
            track_id=track.id,
            collection_item_id=None,
            match_reason=reason,
            confidence=float(track.confidence),
            severity="medium",
            acknowledged=False,
        )
        db.add(alert)
        db.flush()
        created.append(alert)
    return created
