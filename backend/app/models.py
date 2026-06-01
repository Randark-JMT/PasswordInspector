from datetime import datetime, timezone
from sqlalchemy import Index, Text, DateTime, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    domain: Mapped[str] = mapped_column(Text, nullable=False, default="")
    username: Mapped[str] = mapped_column(Text, nullable=False, default="")
    password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    source_file: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        # GIN trigram indexes for fast substring / ILIKE queries on large datasets
        Index("ix_cred_domain_text", "domain", postgresql_using="btree"),
        Index("ix_cred_username_text", "username", postgresql_using="btree"),
        Index("ix_cred_first_seen", "first_seen"),
    )


class FailedLine(Base):
    __tablename__ = "failed_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw: Mapped[str] = mapped_column(Text, nullable=False)
    upload_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[str] = mapped_column(Text, nullable=False, default="")
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    processed_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    total_lines: Mapped[int] = mapped_column(BigInteger, default=0)
    imported_lines: Mapped[int] = mapped_column(BigInteger, default=0)
    failed_lines: Mapped[int] = mapped_column(BigInteger, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
