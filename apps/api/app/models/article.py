from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("doi", name="uq_articles_doi"),
        UniqueConstraint("dedup_hash", name="uq_articles_dedup_hash"),
        Index("ix_articles_journal_published", "journal_id", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("journals.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Text, index=True)
    title_slug: Mapped[str] = mapped_column(String(255), index=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_category: Mapped[str] = mapped_column(String(50), index=True)
    article_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issue: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(100), nullable=True)
    article_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    online_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    print_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_author: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    authors_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(100), index=True)
    source_uid: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
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

    journal = relationship("Journal", back_populates="articles")
    authors = relationship(
        "ArticleAuthor",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleAuthor.position",
    )
    payloads = relationship(
        "ArticlePayload",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticlePayload.fetched_at",
    )


class ArticleAuthor(Base):
    __tablename__ = "article_authors"
    __table_args__ = (
        UniqueConstraint("article_id", "position", name="uq_article_authors_article_position"),
        Index("ix_article_authors_full_name", "full_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[str] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    given_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    affiliation: Mapped[str | None] = mapped_column(Text, nullable=True)

    article = relationship("Article", back_populates="authors")


class ArticlePayload(Base):
    __tablename__ = "article_payloads"
    __table_args__ = (
        Index("ix_article_payloads_article_id_fetched", "article_id", "fetched_at"),
        Index("ix_article_payloads_checksum", "payload_checksum"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[str] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), index=True
    )
    journal_id: Mapped[int] = mapped_column(
        ForeignKey("journals.id", ondelete="CASCADE"), index=True
    )
    source_category: Mapped[str] = mapped_column(String(50), index=True)
    source_name: Mapped[str] = mapped_column(String(100), index=True)
    payload_format: Mapped[str] = mapped_column(String(50))
    payload_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    article = relationship("Article", back_populates="payloads")
