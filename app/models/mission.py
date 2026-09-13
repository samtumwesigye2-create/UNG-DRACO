from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Mission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "missions"

    question: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
