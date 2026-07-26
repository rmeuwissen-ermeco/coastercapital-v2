import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models import (
    AutomationClass,
    CoasterStatus,
    ConfidenceClass,
    EnrichmentEntityType,
    EnrichmentJobStatus,
    EvidenceStatus,
    ProposalStatus,
)

ENRICHABLE_COASTER_FIELDS = {
    "opened_on",
    "height_m",
    "speed_kmh",
    "length_m",
    "summary",
}


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CountryRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str


class ParkBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    country_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opened_on: date | None = None
    website_url: HttpUrl | None = None
    summary: str | None = None
    is_active: bool = True

    @field_validator("name", "city", "summary", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ParkCreate(ParkBase):
    pass


class ParkUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(
        default=None, min_length=2, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    country_id: uuid.UUID | None = None
    city: str | None = Field(default=None, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    opened_on: date | None = None
    website_url: HttpUrl | None = None
    summary: str | None = None
    is_active: bool | None = None


class ParkRead(ParkBase, ORMModel):
    id: uuid.UUID
    country: CountryRead | None
    created_at: datetime
    updated_at: datetime


class ManufacturerBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    country_id: uuid.UUID | None = None
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    website_url: HttpUrl | None = None
    summary: str | None = None
    is_active: bool = True


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(
        default=None, min_length=2, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    country_id: uuid.UUID | None = None
    founded_year: int | None = Field(default=None, ge=1800, le=2100)
    website_url: HttpUrl | None = None
    summary: str | None = None
    is_active: bool | None = None


class ManufacturerRead(ManufacturerBase, ORMModel):
    id: uuid.UUID
    country: CountryRead | None
    created_at: datetime
    updated_at: datetime


class CoasterBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    park_id: uuid.UUID
    manufacturer_id: uuid.UUID | None = None
    status: CoasterStatus = CoasterStatus.UNKNOWN
    opened_on: date | None = None
    height_m: float | None = Field(default=None, ge=0, le=500)
    speed_kmh: float | None = Field(default=None, ge=0, le=500)
    length_m: float | None = Field(default=None, ge=0)
    drop_m: float | None = Field(default=None, ge=0, le=500)
    inversions: int | None = Field(default=None, ge=0, le=50)
    capacity_pph: int | None = Field(default=None, ge=0)
    summary: str | None = None
    is_active: bool = True


class CoasterCreate(CoasterBase):
    pass


class CoasterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    park_id: uuid.UUID | None = None
    manufacturer_id: uuid.UUID | None = None
    status: CoasterStatus | None = None
    opened_on: date | None = None
    height_m: float | None = Field(default=None, ge=0, le=500)
    speed_kmh: float | None = Field(default=None, ge=0, le=500)
    length_m: float | None = Field(default=None, ge=0)
    drop_m: float | None = Field(default=None, ge=0, le=500)
    inversions: int | None = Field(default=None, ge=0, le=50)
    capacity_pph: int | None = Field(default=None, ge=0)
    summary: str | None = None
    is_active: bool | None = None


class CoasterRead(CoasterBase, ORMModel):
    id: uuid.UUID
    park: ParkRead
    manufacturer: ManufacturerRead | None
    created_at: datetime
    updated_at: datetime


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class ParkPage(BaseModel):
    items: list[ParkRead]
    meta: PageMeta


class ManufacturerPage(BaseModel):
    items: list[ManufacturerRead]
    meta: PageMeta


class CoasterPage(BaseModel):
    items: list[CoasterRead]
    meta: PageMeta


class SearchResult(BaseModel):
    entity_type: str
    id: uuid.UUID
    name: str
    subtitle: str | None
    slug: str


class StatsRead(BaseModel):
    parks: int
    manufacturers: int
    coasters: int


class SourceEvidenceRead(ORMModel):
    id: uuid.UUID
    source_type: str
    source_url: str
    source_label: str | None
    asserted_value: object | None
    source_confidence: float | None
    is_primary: bool
    retrieved_at: datetime
    raw_value: object | None


class FieldProposalRead(ORMModel):
    id: uuid.UUID
    field_name: str
    proposed_value: object | None
    reviewed_value: object | None
    current_value: object | None
    evidence_status: EvidenceStatus
    proposal_status: ProposalStatus
    confidence: float
    confidence_class: ConfidenceClass
    automation_class: AutomationClass
    score_breakdown: dict | None
    has_conflict: bool
    auto_approval_eligible: bool
    is_manual_override: bool
    rationale: str | None
    reviewed_at: datetime | None
    evidence: list[SourceEvidenceRead]


class EnrichmentEntityRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class EnrichmentJobCreate(BaseModel):
    entity_type: EnrichmentEntityType = EnrichmentEntityType.COASTER
    entity_id: uuid.UUID | None = None
    coaster_id: uuid.UUID | None = None
    wikidata_id: str | None = Field(default=None, pattern=r"^Q[1-9][0-9]*$")
    official_url: HttpUrl | None = None
    rcdb_url: HttpUrl | None = None
    use_ai: bool = True

    @field_validator("entity_id")
    @classmethod
    def entity_identifier(cls, value: uuid.UUID | None) -> uuid.UUID | None:
        return value


class EnrichmentJobRead(ORMModel):
    id: uuid.UUID
    status: EnrichmentJobStatus
    wikidata_id: str | None
    wikipedia_title: str | None
    source_report: dict | None
    ai_model: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    entity_type: EnrichmentEntityType
    entity_id: uuid.UUID
    entity_match_confidence: float | None
    entity: EnrichmentEntityRead
    coaster: EnrichmentEntityRead | None
    proposals: list[FieldProposalRead]


class ProposalReview(BaseModel):
    decision: ProposalStatus
    value: object | None = None
    override_reason: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def final_decision(cls, value: ProposalStatus) -> ProposalStatus:
        if value in {ProposalStatus.PENDING, ProposalStatus.AUTO_ACCEPTED}:
            raise ValueError("Decision must be a manual review outcome")
        return value


class FieldDefinitionRead(BaseModel):
    entity_type: EnrichmentEntityType
    field_name: str
    label: str
    description: str
    data_type: str
    unit: str | None
    automation_class: AutomationClass
    minimum: float | None
    maximum: float | None
