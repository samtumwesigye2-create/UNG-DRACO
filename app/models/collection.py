from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CollectionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collection_items"

    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    platform: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    entities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    target_acquired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    detection_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
