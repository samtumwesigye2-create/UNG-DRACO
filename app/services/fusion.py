from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectionItem, IntelligenceProduct, Track, TrackItem


def build_assessment(db: Session, track: Track) -> IntelligenceProduct:
    item_ids = db.scalars(
        select(TrackItem.collection_item_id).where(TrackItem.track_id == track.id)
    ).all()
    observations = db.scalars(
        select(CollectionItem).where(CollectionItem.id.in_(item_ids))
    ).all()
    observation_ids = [str(item.id) for item in observations]
    confidence = (
        sum(float(item.confidence) for item in observations) / len(observations)
        if observations
        else float(track.confidence)
    )
    product = IntelligenceProduct(
        summary=f"Track {track.id} fused from {len(observation_ids)} observations",
        confidence=confidence,
        supporting_observations=observation_ids,
        contradictions=[],
        related_entities=[],
        related_tracks=[str(track.id)],
        watch_matches=[],
        mission_relevance=[
            {
                "domain": track.target_type,
                "location": track.location,
                "contributor_count": len(observation_ids),
            }
        ],
        analyst_review_flags=[],
    )
    db.add(product)
    db.flush()
    return product
