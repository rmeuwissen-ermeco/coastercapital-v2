import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
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

    __table_args__ = (
        UniqueConstraint("park_id", "slug", name="uq_coasters_park_slug"),
        Index("ix_coasters_name_park", "name", "park_id"),
    )
