from datetime import UTC, datetime

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    summary="Source-driven roller coaster data with accountable review.",
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.api_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )

