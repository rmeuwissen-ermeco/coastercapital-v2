import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CoasterStatus(str, enum.Enum):
    OPERATING = "operating"
    UNDER_CONSTRUCTION = "under_construction"
    SBNO = "standing_not_operating"
    CLOSED = "closed"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class EnrichmentJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AI_INTERPRETATION = "ai_interpretation"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class ProposalStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        default=UserRole.VIEWER,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="actor")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(index=True)
    changes: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    actor: Mapped[User] = relationship(back_populates="audit_events")


class Country(Base, TimestampMixin):
    __tablename__ = "countries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(2), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

    parks: Mapped[list["Park"]] = relationship(back_populates="country")
    manufacturers: Mapped[list["Manufacturer"]] = relationship(back_populates="country")


class Park(Base, TimestampMixin):
    __tablename__ = "parks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    city: Mapped[str | None] = mapped_column(String(160))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    opened_on: Mapped[date | None] = mapped_column(Date)
    website_url: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    country: Mapped[Country | None] = relationship(back_populates="parks")
    coasters: Mapped[list["Coaster"]] = relationship(back_populates="park")

    __table_args__ = (Index("ix_parks_name_country", "name", "country_id"),)


class Manufacturer(Base, TimestampMixin):
    __tablename__ = "manufacturers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    founded_year: Mapped[int | None] = mapped_column(Integer)
    website_url: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    country: Mapped[Country | None] = relationship(back_populates="manufacturers")
    coasters: Mapped[list["Coaster"]] = relationship(back_populates="manufacturer")


class Coaster(Base, TimestampMixin):
    __tablename__ = "coasters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), index=True)
    slug: Mapped[str] = mapped_column(String(200), index=True)
    park_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parks.id", ondelete="RESTRICT"), index=True
    )
    manufacturer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[CoasterStatus] = mapped_column(
        Enum(
            CoasterStatus,
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        default=CoasterStatus.UNKNOWN,
        index=True,
    )
    opened_on: Mapped[date | None] = mapped_column(Date)
    height_m: Mapped[float | None] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    length_m: Mapped[float | None] = mapped_column(Float)
    drop_m: Mapped[float | None] = mapped_column(Float)
    inversions: Mapped[int | None] = mapped_column(Integer)
    capacity_pph: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    park: Mapped[Park] = relationship(back_populates="coasters")
    manufacturer: Mapped[Manufacturer | None] = relationship(back_populates="coasters")
    enrichment_jobs: Mapped[list["EnrichmentJob"]] = relationship(
        back_populates="coaster", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("park_id", "slug", name="uq_coasters_park_slug"),
        Index("ix_coasters_name_park", "name", "park_id"),
    )


class EnrichmentJob(Base, TimestampMixin):
    __tablename__ = "enrichment_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    coaster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coasters.id", ondelete="CASCADE"), index=True
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[EnrichmentJobStatus] = mapped_column(
        Enum(
            EnrichmentJobStatus,
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        default=EnrichmentJobStatus.PENDING,
        index=True,
    )
    wikidata_id: Mapped[str | None] = mapped_column(String(32), index=True)
    wikipedia_title: Mapped[str | None] = mapped_column(String(300))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    coaster: Mapped[Coaster] = relationship(back_populates="enrichment_jobs")
    requested_by: Mapped[User] = relationship()
    proposals: Mapped[list["FieldProposal"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class FieldProposal(Base, TimestampMixin):
    __tablename__ = "field_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrichment_jobs.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(80), index=True)
    proposed_value: Mapped[object | None] = mapped_column(JSON)
    current_value: Mapped[object | None] = mapped_column(JSON)
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(
            EvidenceStatus,
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        index=True,
    )
    proposal_status: Mapped[ProposalStatus] = mapped_column(
        Enum(
            ProposalStatus,
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        default=ProposalStatus.PENDING,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[EnrichmentJob] = relationship(back_populates="proposals")
    reviewed_by: Mapped[User | None] = relationship()
    evidence: Mapped[list["SourceEvidence"]] = relationship(
        back_populates="proposal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("job_id", "field_name", name="uq_field_proposals_job_field"),
    )


class SourceEvidence(Base):
    __tablename__ = "source_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("field_proposals.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    source_label: Mapped[str | None] = mapped_column(String(300))
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_value: Mapped[object | None] = mapped_column(JSON)

    proposal: Mapped[FieldProposal] = relationship(back_populates="evidence")
