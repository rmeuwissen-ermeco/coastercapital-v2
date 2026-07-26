import uuid

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import Base


def get_or_404[ModelT: Base](db: Session, model: type[ModelT], object_id: uuid.UUID) -> ModelT:
    item = db.get(model, object_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return item


def commit[ModelT: Base](db: Session, item: ModelT) -> ModelT:
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A record with this identifier already exists",
        ) from exc


def apply_update[ModelT: Base](item: ModelT, data: BaseModel) -> ModelT:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, str(value) if field == "website_url" and value else value)
    return item


def record_audit(
    db: Session,
    *,
    actor: models.User,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    changes: dict | None,
) -> None:
    db.add(
        models.AuditEvent(
            actor_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
        )
    )
    db.commit()


def list_parks(db: Session, *, limit: int, offset: int, query: str | None) -> schemas.ParkPage:
    filters = []
    if query:
        filters.append(models.Park.name.ilike(f"%{query}%"))
    total = db.scalar(select(func.count()).select_from(models.Park).where(*filters)) or 0
    statement = (
        select(models.Park)
        .options(selectinload(models.Park.country))
        .where(*filters)
        .order_by(models.Park.name)
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(statement).all())
    return schemas.ParkPage(
        items=items, meta=schemas.PageMeta(limit=limit, offset=offset, total=total)
    )


def list_manufacturers(
    db: Session, *, limit: int, offset: int, query: str | None
) -> schemas.ManufacturerPage:
    filters = []
    if query:
        filters.append(models.Manufacturer.name.ilike(f"%{query}%"))
    total = db.scalar(select(func.count()).select_from(models.Manufacturer).where(*filters)) or 0
    statement = (
        select(models.Manufacturer)
        .options(selectinload(models.Manufacturer.country))
        .where(*filters)
        .order_by(models.Manufacturer.name)
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(statement).all())
    return schemas.ManufacturerPage(
        items=items, meta=schemas.PageMeta(limit=limit, offset=offset, total=total)
    )


def coaster_load_options():
    return (
        selectinload(models.Coaster.park).selectinload(models.Park.country),
        selectinload(models.Coaster.manufacturer).selectinload(models.Manufacturer.country),
    )


def list_coasters(
    db: Session,
    *,
    limit: int,
    offset: int,
    query: str | None,
    park_id: uuid.UUID | None,
) -> schemas.CoasterPage:
    filters = []
    if query:
        filters.append(models.Coaster.name.ilike(f"%{query}%"))
    if park_id:
        filters.append(models.Coaster.park_id == park_id)
    total = db.scalar(select(func.count()).select_from(models.Coaster).where(*filters)) or 0
    statement = (
        select(models.Coaster)
        .options(*coaster_load_options())
        .where(*filters)
        .order_by(models.Coaster.name)
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(statement).all())
    return schemas.CoasterPage(
        items=items, meta=schemas.PageMeta(limit=limit, offset=offset, total=total)
    )


def search(db: Session, query: str, limit: int) -> list[schemas.SearchResult]:
    needle = f"%{query}%"
    results: list[schemas.SearchResult] = []

    coaster_statement = (
        select(models.Coaster)
        .options(selectinload(models.Coaster.park))
        .where(models.Coaster.name.ilike(needle))
        .order_by(models.Coaster.name)
        .limit(limit)
    )
    for coaster in db.scalars(coaster_statement):
        results.append(
            schemas.SearchResult(
                entity_type="coaster",
                id=coaster.id,
                name=coaster.name,
                subtitle=coaster.park.name,
                slug=coaster.slug,
            )
        )

    remaining = max(0, limit - len(results))
    if remaining:
        park_statement = (
            select(models.Park)
            .where(or_(models.Park.name.ilike(needle), models.Park.city.ilike(needle)))
            .order_by(models.Park.name)
            .limit(remaining)
        )
        for park in db.scalars(park_statement):
            results.append(
                schemas.SearchResult(
                    entity_type="park",
                    id=park.id,
                    name=park.name,
                    subtitle=park.city,
                    slug=park.slug,
                )
            )
    return results
