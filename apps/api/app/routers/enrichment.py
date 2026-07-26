import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import confidence, data_catalog, enrichment, models, research, schemas
from app.auth import require_roles
from app.config import get_settings
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
        settings = get_settings()
        source_report: dict[str, object] = {
            "wikimedia": {"status": "pending", "assertions": 0},
            "official": {"status": "not_requested", "assertions": 0},
            "rcdb": {"status": "not_requested", "assertions": 0},
            "ai": {
                "status": (
                    "enabled"
                    if payload.use_ai and settings.openai_api_key
                    else "disabled_no_key"
                    if payload.use_ai
                    else "disabled_by_request"
                )
            },
            "warnings": [],
        }
        candidates: list[enrichment.EvidenceCandidate] = []
        try:
            qid, wikipedia_title, wikimedia_candidates = enrichment.fetch_candidates(
                coaster_name=entity.name,
                park_name=context_name,
                wikidata_id=payload.wikidata_id,
            )
            candidates.extend(wikimedia_candidates)
            job.wikidata_id = qid
            job.wikipedia_title = wikipedia_title
            source_report["wikimedia"].update(
                status="ok", assertions=len(wikimedia_candidates)
            )
        except enrichment.EnrichmentLookupError as exc:
            source_report["wikimedia"].update(status="failed", error=str(exc))
            source_report["warnings"].append(str(exc))
        job.entity_match_confidence = 0.99 if payload.wikidata_id else 0.90
        page_sources = _page_sources(payload, entity)
        for source in page_sources:
            source_state = source_report[source.source_type]
            try:
                page_text = research.fetch_page_text(source, settings)
                extracted = (
                    research.extract_assertions(
                        entity_type=payload.entity_type,
                        entity_name=entity.name,
                        context_name=context_name,
                        source=source,
                        page_text=page_text,
                        settings=settings,
                    )
                    if payload.use_ai
                    else []
                )
                candidates.extend(extracted)
                source_state.update(status="ok", assertions=len(extracted))
            except research.ResearchError as exc:
                source_state.update(status="failed", error=str(exc))
                source_report["warnings"].append(str(exc))
        job.source_report = source_report
        job.ai_model = (
            settings.openai_model
            if payload.use_ai and settings.openai_api_key
            else None
        )
        if not candidates:
            raise research.ResearchError(
                "No usable source assertions were found; canonical data was not changed"
            )
        grouped: dict[str, list[enrichment.EvidenceCandidate]] = defaultdict(list)
        for candidate in candidates:
            grouped[candidate.field_name].append(candidate)
        for field_name, field_candidates in grouped.items():
            definition = data_catalog.field_definition(payload.entity_type, field_name)
            if definition is None or not hasattr(entity, field_name):
                continue
            synthesis = None
            if payload.use_ai and settings.openai_api_key and len(field_candidates) > 1:
                try:
                    synthesis = research.synthesize_field(
                        entity_type=payload.entity_type,
                        entity_name=entity.name,
                        field_name=field_name,
                        candidates=field_candidates,
                        settings=settings,
                    )
                except research.ResearchError as exc:
                    source_report["warnings"].append(str(exc))
                    source_report["ai"]["status"] = "partial_failure"
            selected = _select_candidate(field_candidates, synthesis)
            current = getattr(entity, field_name)
            is_valid = data_catalog.validate_value(definition, selected.value)
            domains = {
                item.independence_key or urlparse(item.source_url).hostname or item.source_type
                for item in field_candidates
            }
            has_primary = any(item.is_primary for item in field_candidates)
            has_conflict = len(research.distinct_values(field_candidates)) > 1
            agreement = _agreement(field_candidates, selected.value)
            semantic_fit = synthesis.semantic_fit if synthesis else 0.90
            source_quality = max(item.confidence for item in field_candidates)
            score = confidence.calculate(
                confidence.ScoreInput(
                    entity_match=job.entity_match_confidence,
                    source_quality=source_quality,
                    agreement=agreement,
                    semantic_fit=semantic_fit,
                    freshness=0.80,
                    validation=1.0 if is_valid else 0.0,
                    independent_sources=len(domains),
                    has_primary_source=has_primary,
                    has_conflict=has_conflict,
                ),
                definition.automation_class,
            )
            proposal = models.FieldProposal(
                job_id=job.id,
                field_name=field_name,
                proposed_value=selected.value,
                current_value=_json_value(current),
                evidence_status=(
                    models.EvidenceStatus.CONFLICTING
                    if has_conflict
                    else models.EvidenceStatus.PROBABLE
                ),
                confidence=score.confidence,
                confidence_class=score.confidence_class,
                automation_class=definition.automation_class,
                score_breakdown=score.breakdown,
                has_conflict=has_conflict,
                auto_approval_eligible=score.auto_approval_eligible,
                rationale=_rationale(field_candidates, synthesis, has_conflict),
            )
            for item in field_candidates:
                proposal.evidence.append(
                    models.SourceEvidence(
                        source_type=item.source_type,
                        source_url=item.source_url,
                        source_label=item.source_label,
                        asserted_value=item.value,
                        source_confidence=item.confidence,
                        raw_value=item.raw_value,
                        is_primary=item.is_primary,
                    )
                )
            db.add(proposal)
            if score.auto_approval_eligible and not _has_active_override(
                db, payload.entity_type, entity.id, field_name
            ):
                _apply_value(entity, field_name, selected.value)
                proposal.proposal_status = models.ProposalStatus.AUTO_ACCEPTED
                proposal.reviewed_value = selected.value
                proposal.reviewed_at = datetime.now(UTC)
                db.add(entity)
        job.status = models.EnrichmentJobStatus.REVIEW
        job.finished_at = datetime.now(UTC)
        db.commit()
    except (enrichment.EnrichmentLookupError, research.ResearchError) as exc:
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


def _page_sources(
    payload: schemas.EnrichmentJobCreate,
    entity: models.Coaster | models.Park | models.Manufacturer,
) -> list[research.PageSource]:
    sources: list[research.PageSource] = []
    official_url = str(payload.official_url) if payload.official_url else None
    if official_url is None:
        if isinstance(entity, (models.Park, models.Manufacturer)):
            official_url = entity.website_url
        elif isinstance(entity, models.Coaster):
            official_url = entity.park.website_url
    if official_url:
        sources.append(
            research.PageSource(
                source_type="official",
                url=str(official_url),
                label=f"Official website · {entity.name}",
                is_primary=True,
            )
        )
    if payload.rcdb_url:
        sources.append(
            research.PageSource(
                source_type="rcdb",
                url=str(payload.rcdb_url),
                label=f"RCDB · {entity.name}",
                is_primary=False,
            )
        )
    return sources


def _select_candidate(
    candidates: list[enrichment.EvidenceCandidate],
    synthesis: research.SynthesisResult | None,
) -> enrichment.EvidenceCandidate:
    if synthesis is not None:
        supporting = [candidates[index] for index in synthesis.supporting_indexes]
        best = max(supporting, key=lambda item: (item.is_primary, item.confidence))
        return enrichment.EvidenceCandidate(
            field_name=synthesis.field_name,
            value=synthesis.value,
            source_type=best.source_type,
            source_url=best.source_url,
            source_label=best.source_label,
            confidence=synthesis.confidence,
            raw_value=best.raw_value,
            is_primary=best.is_primary,
            independence_key=best.independence_key,
        )
    return max(candidates, key=lambda item: (item.is_primary, item.confidence))


def _agreement(
    candidates: list[enrichment.EvidenceCandidate], selected_value: object
) -> float:
    selected = str(selected_value).strip().casefold()
    agreeing = sum(
        1 for item in candidates if str(item.value).strip().casefold() == selected
    )
    return agreeing / len(candidates)


def _rationale(
    candidates: list[enrichment.EvidenceCandidate],
    synthesis: research.SynthesisResult | None,
    has_conflict: bool,
) -> str:
    if synthesis:
        prefix = "Conflicting assertions require review. " if has_conflict else ""
        return prefix + synthesis.rationale
    if has_conflict:
        return (
            f"{len(candidates)} source assertions disagree. The highest-quality assertion "
            "is proposed, but automatic approval is blocked."
        )
    if len(candidates) == 1:
        return (
            "One source assertion was found. Editorial review remains required until "
            "independent or primary evidence confirms it."
        )
    return f"{len(candidates)} source assertions support the proposed canonical value."


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
