import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import crud, models, schemas
from app.auth import require_roles
from app.database import get_db

router = APIRouter(prefix="/v1", tags=["catalogue"])
DbSession = Annotated[Session, Depends(get_db)]
Editor = Annotated[
    models.User,
    Depends(require_roles(models.UserRole.ADMIN, models.UserRole.EDITOR)),
]


@router.get("/countries", response_model=list[schemas.CountryRead])
def countries(db: DbSession) -> list[models.Country]:
    return list(db.scalars(select(models.Country).order_by(models.Country.name)).all())


@router.get("/stats", response_model=schemas.StatsRead)
def stats(db: DbSession) -> schemas.StatsRead:
    return schemas.StatsRead(
        parks=db.scalar(select(func.count()).select_from(models.Park)) or 0,
        manufacturers=db.scalar(select(func.count()).select_from(models.Manufacturer)) or 0,
        coasters=db.scalar(select(func.count()).select_from(models.Coaster)) or 0,
    )


@router.get("/parks", response_model=schemas.ParkPage)
def parks(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[str | None, Query(max_length=100)] = None,
) -> schemas.ParkPage:
    return crud.list_parks(db, limit=limit, offset=offset, query=query)


@router.post("/parks", response_model=schemas.ParkRead, status_code=status.HTTP_201_CREATED)
def create_park(data: schemas.ParkCreate, db: DbSession, actor: Editor) -> models.Park:
    item = crud.commit(
        db,
        models.Park(
            **data.model_dump(exclude={"website_url"}),
            website_url=str(data.website_url) if data.website_url else None,
        ),
    )
    crud.record_audit(
        db,
        actor=actor,
        action="create",
        entity_type="park",
        entity_id=item.id,
        changes=data.model_dump(mode="json"),
    )
    return item


@router.get("/parks/{park_id}", response_model=schemas.ParkRead)
def park(park_id: uuid.UUID, db: DbSession) -> models.Park:
    statement = (
        select(models.Park)
        .options(selectinload(models.Park.country))
        .where(models.Park.id == park_id)
    )
    item = db.scalar(statement)
    if item is None:
        return crud.get_or_404(db, models.Park, park_id)
    return item


@router.patch("/parks/{park_id}", response_model=schemas.ParkRead)
def update_park(
    park_id: uuid.UUID, data: schemas.ParkUpdate, db: DbSession, actor: Editor
) -> models.Park:
    item = crud.commit(db, crud.apply_update(crud.get_or_404(db, models.Park, park_id), data))
    crud.record_audit(
        db,
        actor=actor,
        action="update",
        entity_type="park",
        entity_id=item.id,
        changes=data.model_dump(mode="json", exclude_unset=True),
    )
    return item


@router.delete("/parks/{park_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_park(park_id: uuid.UUID, db: DbSession, actor: Editor) -> Response:
    item = crud.get_or_404(db, models.Park, park_id)
    item.is_active = False
    db.commit()
    crud.record_audit(
        db,
        actor=actor,
        action="deactivate",
        entity_type="park",
        entity_id=item.id,
        changes={"is_active": False},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/manufacturers", response_model=schemas.ManufacturerPage)
def manufacturers(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[str | None, Query(max_length=100)] = None,
) -> schemas.ManufacturerPage:
    return crud.list_manufacturers(db, limit=limit, offset=offset, query=query)


@router.post(
    "/manufacturers",
    response_model=schemas.ManufacturerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_manufacturer(
    data: schemas.ManufacturerCreate, db: DbSession, actor: Editor
) -> models.Manufacturer:
    item = crud.commit(
        db,
        models.Manufacturer(
            **data.model_dump(exclude={"website_url"}),
            website_url=str(data.website_url) if data.website_url else None,
        ),
    )
    crud.record_audit(
        db,
        actor=actor,
        action="create",
        entity_type="manufacturer",
        entity_id=item.id,
        changes=data.model_dump(mode="json"),
    )
    return item


@router.patch("/manufacturers/{manufacturer_id}", response_model=schemas.ManufacturerRead)
def update_manufacturer(
    manufacturer_id: uuid.UUID,
    data: schemas.ManufacturerUpdate,
    db: DbSession,
    actor: Editor,
) -> models.Manufacturer:
    item = crud.commit(
        db,
        crud.apply_update(
            crud.get_or_404(db, models.Manufacturer, manufacturer_id),
            data,
        ),
    )
    crud.record_audit(
        db,
        actor=actor,
        action="update",
        entity_type="manufacturer",
        entity_id=item.id,
        changes=data.model_dump(mode="json", exclude_unset=True),
    )
    return item


@router.get("/coasters", response_model=schemas.CoasterPage)
def coasters(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[str | None, Query(max_length=100)] = None,
    park_id: uuid.UUID | None = None,
) -> schemas.CoasterPage:
    return crud.list_coasters(db, limit=limit, offset=offset, query=query, park_id=park_id)


@router.post("/coasters", response_model=schemas.CoasterRead, status_code=status.HTTP_201_CREATED)
def create_coaster(data: schemas.CoasterCreate, db: DbSession, actor: Editor) -> models.Coaster:
    crud.get_or_404(db, models.Park, data.park_id)
    if data.manufacturer_id:
        crud.get_or_404(db, models.Manufacturer, data.manufacturer_id)
    item = crud.commit(db, models.Coaster(**data.model_dump()))
    crud.record_audit(
        db,
        actor=actor,
        action="create",
        entity_type="coaster",
        entity_id=item.id,
        changes=data.model_dump(mode="json"),
    )
    statement = (
        select(models.Coaster)
        .options(*crud.coaster_load_options())
        .where(models.Coaster.id == item.id)
    )
    return db.scalar(statement) or item


@router.patch("/coasters/{coaster_id}", response_model=schemas.CoasterRead)
def update_coaster(
    coaster_id: uuid.UUID,
    data: schemas.CoasterUpdate,
    db: DbSession,
    actor: Editor,
) -> models.Coaster:
    item = crud.commit(db, crud.apply_update(crud.get_or_404(db, models.Coaster, coaster_id), data))
    crud.record_audit(
        db,
        actor=actor,
        action="update",
        entity_type="coaster",
        entity_id=item.id,
        changes=data.model_dump(mode="json", exclude_unset=True),
    )
    statement = (
        select(models.Coaster)
        .options(*crud.coaster_load_options())
        .where(models.Coaster.id == item.id)
    )
    return db.scalar(statement) or item


@router.get("/search", response_model=list[schemas.SearchResult])
def global_search(
    db: DbSession,
    query: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> list[schemas.SearchResult]:
    return crud.search(db, query=query, limit=limit)
