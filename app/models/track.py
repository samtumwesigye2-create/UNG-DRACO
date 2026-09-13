from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Track(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tracks"

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fusion_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class TrackItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "track_items"
    __table_args__ = (UniqueConstraint("track_id", "collection_item_id", name="uq_track_collection_item"),)

    track_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("collection_items.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
