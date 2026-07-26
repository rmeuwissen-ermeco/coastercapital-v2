from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/v1/auth", tags=["authentication"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Invalid email address")
        return normalized


class UserRead(BaseModel):
    id: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


def user_read(user: User) -> UserRead:
    return UserRead(id=str(user.id), email=user.email, role=user.role.value)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: DbSession) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return LoginResponse(access_token=create_access_token(user), user=user_read(user))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return user_read(user)
