from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    journal_name: Mapped[str] = mapped_column(String(255), index=True)
    publisher: Mapped[str] = mapped_column(String(255), index=True)
    adapter_key: Mapped[str] = mapped_column(String(100))
    issn_print: Mapped[str | None] = mapped_column(String(32), nullable=True)
    issn_online: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rss_current_issue_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rss_online_first_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    crossref_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    homepage_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    update_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    polling_strategy: Mapped[str] = mapped_column(String(100))
    primary_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    articles = relationship("Article", back_populates="journal", cascade="all, delete-orphan")
    source_states = relationship(
        "SourceState", back_populates="journal", cascade="all, delete-orphan"
    )


class SourceState(Base):
    __tablename__ = "source_states"
    __table_args__ = (
        UniqueConstraint(
            "journal_id",
            "source_category",
            "source_name",
            name="uq_source_states_journal_category_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("journals.id", ondelete="CASCADE"), index=True
    )
    source_category: Mapped[str] = mapped_column(String(50), index=True)
    source_name: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_seen_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    journal = relationship("Journal", back_populates="source_states")
