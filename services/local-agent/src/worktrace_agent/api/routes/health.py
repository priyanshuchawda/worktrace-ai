from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from worktrace_agent import __version__
from worktrace_agent.db.migrations import get_latest_schema_version

APP_NAME = "worktrace-local-agent"

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str
    app_version: str
    schema_version: str
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(
        app_name=APP_NAME,
        app_version=__version__,
        schema_version=get_latest_schema_version(),
        status="ok",
    )
