import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import confidence, data_catalog, enrichment, models, schemas
from app.auth import require_roles
from app.crud import get_or_404, record_audit
from app.database import get_db

router = APIRouter(prefix="/v1/admin/enrichment", tags=["enrichment"])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[models.User, Depends(require_roles(models.UserRole.ADMIN))]


def _load_job(db: Session, job_id: uuid.UUID) -> models.EnrichmentJob:
    statement = (
        select(models.EnrichmentJob)
        .options(
            selectinload(models.EnrichmentJob.coaster).selectinload(models.Coaster.park),
            selectinload(models.EnrichmentJob.park),
            selectinload(models.EnrichmentJob.manufacturer),
            selectinload(models.EnrichmentJob.proposals).selectinload(
                models.FieldProposal.evidence
            ),
        )
        .where(models.EnrichmentJob.id == job_id)
    )
    job = db.scalar(statement)
    if job is None:
        raise HTTPException(status_code=404, detail="Enrichment job not found")
    return job


@router.get("/jobs", response_model=list[schemas.EnrichmentJobRead])
def list_jobs(db: DbSession, _: AdminUser) -> list[models.EnrichmentJob]:
    statement = (
        select(models.EnrichmentJob)
        .options(
            selectinload(models.EnrichmentJob.coaster),
            selectinload(models.EnrichmentJob.park),
            selectinload(models.EnrichmentJob.manufacturer),
            selectinload(models.EnrichmentJob.proposals).selectinload(
                models.FieldProposal.evidence
            ),
        )
        .order_by(models.EnrichmentJob.created_at.desc())
        .limit(100)
    )
    return list(db.scalars(statement).unique().all())


@router.get("/catalog", response_model=list[schemas.FieldDefinitionRead])
def get_catalog(_: AdminUser) -> list[dict]:
    return data_catalog.public_catalog()


@router.post("/jobs", response_model=schemas.EnrichmentJobRead, status_code=201)
def create_job(
    payload: schemas.EnrichmentJobCreate, db: DbSession, actor: AdminUser
) -> models.EnrichmentJob:
    entity_id = payload.entity_id or payload.coaster_id
    if entity_id is None:
        raise HTTPException(status_code=422, detail="entity_id is required")
    entity = _get_entity(db, payload.entity_type, entity_id)
    context_name = ""
    if isinstance(entity, models.Coaster):
        db.refresh(entity, attribute_names=["park"])
        context_name = entity.park.name
    elif isinstance(entity, models.Park):
        context_name = entity.city or ""
    job = models.EnrichmentJob(
        coaster_id=entity.id if isinstance(entity, models.Coaster) else None,
        park_id=entity.id if isinstance(entity, models.Park) else None,
        manufacturer_id=entity.id if isinstance(entity, models.Manufacturer) else None,
        entity_type=payload.entity_type,
        entity_id=entity.id,
        requested_by_id=actor.id,
        status=models.EnrichmentJobStatus.RUNNING,
        wikidata_id=payload.wikidata_id,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        qid, wikipedia_title, candidates = enrichment.fetch_candidates(
            coaster_name=entity.name,
            park_name=context_name,
            wikidata_id=payload.wikidata_id,
        )
        job.wikidata_id = qid
        job.wikipedia_title = wikipedia_title
        job.entity_match_confidence = 0.99 if payload.wikidata_id else 0.90
        for candidate in candidates:
            definition = data_catalog.field_definition(payload.entity_type, candidate.field_name)
            if definition is None or not hasattr(entity, candidate.field_name):
                continue
            current = getattr(entity, candidate.field_name)
            is_valid = data_catalog.validate_value(definition, candidate.value)
            score = confidence.calculate(
                confidence.ScoreInput(
                    entity_match=job.entity_match_confidence,
                    source_quality=candidate.confidence,
                    agreement=candidate.confidence,
                    semantic_fit=0.90,
                    freshness=0.80,
                    validation=1.0 if is_valid else 0.0,
                    independent_sources=1,
                    has_primary_source=False,
                ),
                definition.automation_class,
            )
            proposal = models.FieldProposal(
                job_id=job.id,
                field_name=candidate.field_name,
                proposed_value=candidate.value,
                current_value=_json_value(current),
                evidence_status=models.EvidenceStatus.PROBABLE,
                confidence=score.confidence,
                confidence_class=score.confidence_class,
                automation_class=definition.automation_class,
                score_breakdown=score.breakdown,
                auto_approval_eligible=score.auto_approval_eligible,
                rationale=(
                    "One source assertion was found. The value remains subject to "
                    "editorial review until independent or primary evidence confirms it."
                ),
            )
            proposal.evidence.append(
                models.SourceEvidence(
                    source_type=candidate.source_type,
                    source_url=candidate.source_url,
                    source_label=candidate.source_label,
                    asserted_value=candidate.value,
                    source_confidence=candidate.confidence,
                    raw_value=candidate.raw_value,
                )
            )
            db.add(proposal)
            if score.auto_approval_eligible and not _has_active_override(
                db, payload.entity_type, entity.id, candidate.field_name
            ):
                _apply_value(entity, candidate.field_name, candidate.value)
                proposal.proposal_status = models.ProposalStatus.AUTO_ACCEPTED
                proposal.reviewed_value = candidate.value
                proposal.reviewed_at = datetime.now(UTC)
                db.add(entity)
        job.status = models.EnrichmentJobStatus.REVIEW
        job.finished_at = datetime.now(UTC)
        db.commit()
    except enrichment.EnrichmentLookupError as exc:
        job.status = models.EnrichmentJobStatus.FAILED
        job.error_message = str(exc)
        job.finished_at = datetime.now(UTC)
        db.commit()
    record_audit(
        db,
        actor=actor,
        action="enrichment.run",
        entity_type="enrichment_job",
        entity_id=job.id,
        changes={
            "entity_type": payload.entity_type.value,
            "entity_id": str(entity.id),
            "status": job.status.value,
        },
    )
    return _load_job(db, job.id)


@router.patch("/proposals/{proposal_id}", response_model=schemas.FieldProposalRead)
def review_proposal(
    proposal_id: uuid.UUID,
    payload: schemas.ProposalReview,
    db: DbSession,
    actor: AdminUser,
) -> models.FieldProposal:
    proposal = get_or_404(db, models.FieldProposal, proposal_id)
    db.refresh(proposal, attribute_names=["job"])
    if proposal.proposal_status != models.ProposalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Proposal has already been reviewed")
    entity = _get_entity(db, proposal.job.entity_type, proposal.job.entity_id)
    if payload.decision == models.ProposalStatus.ACCEPTED:
        definition = data_catalog.field_definition(
            proposal.job.entity_type, proposal.field_name
        )
        if definition is None:
            raise HTTPException(status_code=422, detail="Field cannot be applied automatically")
        final_value = (
            payload.value if payload.value is not None else proposal.proposed_value
        )
        if not data_catalog.validate_value(definition, final_value):
            raise HTTPException(status_code=422, detail="Value does not satisfy the data catalog")
        is_override = payload.value is not None and payload.value != proposal.proposed_value
        if is_override and not payload.override_reason:
            raise HTTPException(
                status_code=422, detail="A reason is required when correcting a proposal"
            )
        _apply_value(entity, proposal.field_name, final_value)
        proposal.reviewed_value = final_value
        proposal.is_manual_override = is_override
        if is_override:
            _upsert_override(
                db,
                actor,
                proposal.job.entity_type,
                entity.id,
                proposal.field_name,
                final_value,
                payload.override_reason or "",
            )
        db.add(entity)
    proposal.proposal_status = payload.decision
    proposal.reviewed_by_id = actor.id
    proposal.reviewed_at = datetime.now(UTC)
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    pending = db.scalar(
        select(func.count())
        .select_from(models.FieldProposal)
        .where(
            models.FieldProposal.job_id == proposal.job_id,
            models.FieldProposal.proposal_status == models.ProposalStatus.PENDING,
        )
    )
    if not pending:
        proposal.job.status = models.EnrichmentJobStatus.COMPLETED
        db.add(proposal.job)
        db.commit()
    record_audit(
        db,
        actor=actor,
        action=f"enrichment.{payload.decision.value}",
        entity_type="field_proposal",
        entity_id=proposal.id,
        changes={
            "entity_type": proposal.job.entity_type.value,
            "entity_id": str(entity.id),
            "field": proposal.field_name,
            "proposed_value": proposal.proposed_value,
            "reviewed_value": proposal.reviewed_value,
            "override_reason": payload.override_reason,
        },
    )
    return proposal


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, models.CoasterStatus):
        return value.value
    return value


def _entity_value(field_name: str, value: object) -> object:
    if field_name == "opened_on" and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _apply_value(entity: object, field_name: str, value: object) -> None:
    setattr(entity, field_name, _entity_value(field_name, value))


def _get_entity(
    db: Session, entity_type: models.EnrichmentEntityType, entity_id: uuid.UUID
) -> models.Coaster | models.Park | models.Manufacturer:
    entity_models = {
        models.EnrichmentEntityType.COASTER: models.Coaster,
        models.EnrichmentEntityType.PARK: models.Park,
        models.EnrichmentEntityType.MANUFACTURER: models.Manufacturer,
    }
    return get_or_404(db, entity_models[entity_type], entity_id)


def _has_active_override(
    db: Session,
    entity_type: models.EnrichmentEntityType,
    entity_id: uuid.UUID,
    field_name: str,
) -> bool:
    return (
        db.scalar(
            select(models.CanonicalOverride.id).where(
                models.CanonicalOverride.entity_type == entity_type,
                models.CanonicalOverride.entity_id == entity_id,
                models.CanonicalOverride.field_name == field_name,
                models.CanonicalOverride.is_active.is_(True),
            )
        )
        is not None
    )


def _upsert_override(
    db: Session,
    actor: models.User,
    entity_type: models.EnrichmentEntityType,
    entity_id: uuid.UUID,
    field_name: str,
    value: object,
    reason: str,
) -> None:
    override = db.scalar(
        select(models.CanonicalOverride).where(
            models.CanonicalOverride.entity_type == entity_type,
            models.CanonicalOverride.entity_id == entity_id,
            models.CanonicalOverride.field_name == field_name,
        )
    )
    if override is None:
        override = models.CanonicalOverride(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            created_by_id=actor.id,
        )
    override.value = value
    override.reason = reason
    override.is_active = True
    db.add(override)
