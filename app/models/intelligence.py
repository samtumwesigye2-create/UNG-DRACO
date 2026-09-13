from sqlalchemy import Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IntelligenceProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_products"

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_observations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    contradictions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    related_entities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    related_tracks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    watch_matches: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mission_relevance: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    analyst_review_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
