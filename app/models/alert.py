from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    watch_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("collection_items.id", ondelete="SET NULL"), nullable=True, index=True)
    track_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True, index=True)
    match_reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
