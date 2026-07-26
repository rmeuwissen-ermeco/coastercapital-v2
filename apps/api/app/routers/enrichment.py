import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import enrichment, models, schemas
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
            selectinload(models.EnrichmentJob.proposals).selectinload(
                models.FieldProposal.evidence
            ),
        )
        .order_by(models.EnrichmentJob.created_at.desc())
        .limit(100)
    )
    return list(db.scalars(statement).unique().all())


@router.post("/jobs", response_model=schemas.EnrichmentJobRead, status_code=201)
def create_job(
    payload: schemas.EnrichmentJobCreate, db: DbSession, actor: AdminUser
) -> models.EnrichmentJob:
    coaster = get_or_404(db, models.Coaster, payload.coaster_id)
    db.refresh(coaster, attribute_names=["park"])
    job = models.EnrichmentJob(
        coaster_id=coaster.id,
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
            coaster_name=coaster.name,
            park_name=coaster.park.name,
            wikidata_id=payload.wikidata_id,
        )
        job.wikidata_id = qid
        job.wikipedia_title = wikipedia_title
        for candidate in candidates:
            current = getattr(coaster, candidate.field_name)
            proposal = models.FieldProposal(
                job_id=job.id,
                field_name=candidate.field_name,
                proposed_value=candidate.value,
                current_value=_json_value(current),
                evidence_status=models.EvidenceStatus.PROBABLE,
                confidence=candidate.confidence,
                rationale="Single external source; requires editorial review.",
            )
            proposal.evidence.append(
                models.SourceEvidence(
                    source_type=candidate.source_type,
                    source_url=candidate.source_url,
                    source_label=candidate.source_label,
                    raw_value=candidate.raw_value,
                )
            )
            db.add(proposal)
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
        changes={"coaster_id": str(coaster.id), "status": job.status.value},
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
    coaster = get_or_404(db, models.Coaster, proposal.job.coaster_id)
    if payload.decision == models.ProposalStatus.ACCEPTED:
        if proposal.field_name not in schemas.ENRICHABLE_COASTER_FIELDS:
            raise HTTPException(status_code=422, detail="Field cannot be applied automatically")
        setattr(
            coaster,
            proposal.field_name,
            _coaster_value(proposal.field_name, proposal.proposed_value),
        )
        db.add(coaster)
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
            "coaster_id": str(coaster.id),
            "field": proposal.field_name,
            "value": proposal.proposed_value,
        },
    )
    return proposal


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, models.CoasterStatus):
        return value.value
    return value


def _coaster_value(field_name: str, value: object) -> object:
    if field_name == "opened_on" and isinstance(value, str):
        return date.fromisoformat(value)
    return value
