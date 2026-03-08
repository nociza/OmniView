from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()
