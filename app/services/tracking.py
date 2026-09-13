from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectionItem, Track, TrackItem


def _confidence(items: list[CollectionItem]) -> float:
    if not items:
        return 0.0
    return sum(float(item.confidence) for item in items) / len(items)


def upsert_track(db: Session, observation: CollectionItem, related: list[CollectionItem]) -> Track:
    observation_ids = [observation.id, *(item.id for item in related)]
    track = db.scalar(
        select(Track)
        .join(TrackItem, TrackItem.track_id == Track.id)
        .where(TrackItem.collection_item_id.in_(observation_ids), Track.status != "CLOSED")
        .order_by(Track.created_at.asc())
        .limit(1)
    )

    contributors = [observation, *related]
    if track is None:
        track = Track(
            status="DETECTED",
            confidence=_confidence(contributors),
            location=observation.location,
            target_type=observation.domain,
            fusion_explanation={"domain": observation.domain, "contributor_count": len(contributors)},
        )
        db.add(track)
        db.flush()
    else:
        track.status = "UPDATED"
        track.location = observation.location or track.location
        track.target_type = observation.domain

    existing_ids = set(
        db.scalars(select(TrackItem.collection_item_id).where(TrackItem.track_id == track.id)).all()
    )
    for item in contributors:
        if item.id in existing_ids:
            continue
        db.add(
            TrackItem(
                track_id=track.id,
                collection_item_id=item.id,
                match_score=float(item.confidence),
            )
        )
        existing_ids.add(item.id)

    db.flush()
    all_item_ids = db.scalars(
        select(TrackItem.collection_item_id).where(TrackItem.track_id == track.id)
    ).all()
    all_items = db.scalars(select(CollectionItem).where(CollectionItem.id.in_(all_item_ids))).all()
    track.confidence = _confidence(list(all_items))
    if track.status == "DETECTED" and len(all_item_ids) > 1:
        track.status = "ACTIVE"
    track.fusion_explanation = {
        "domain": observation.domain,
        "contributor_count": len(all_item_ids),
        "observation_ids": [str(item_id) for item_id in all_item_ids],
    }
    db.flush()
    return track
