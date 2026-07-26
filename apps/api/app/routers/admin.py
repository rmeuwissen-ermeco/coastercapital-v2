import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_roles
from app.database import get_db
from app.models import AuditEvent, User, UserRole

router = APIRouter(prefix="/v1/admin", tags=["administration"])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


class AuditActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    changes: dict | None
    created_at: datetime
    actor: AuditActor


@router.get("/audit-events", response_model=list[AuditEventRead])
def audit_events(
    db: DbSession,
    _: AdminUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditEvent]:
    statement = (
        select(AuditEvent)
        .options(selectinload(AuditEvent.actor))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
