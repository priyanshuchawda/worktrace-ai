from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from worktrace_agent.privacy.config import (
    MAX_POLICY_ENTRIES,
    PrivacyPolicyConfig,
    PrivacyPolicyConfigError,
    PrivacyPolicyConfigService,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])


class PrivacyPolicyConfigRequest(BaseModel):
    allowlist: list[str] = Field(default_factory=list, max_length=MAX_POLICY_ENTRIES)
    blocklist: list[str] = Field(default_factory=list, max_length=MAX_POLICY_ENTRIES)
    clipboard_safe_mode: bool = True


class PrivacyPolicyConfigResponse(BaseModel):
    allowlist: list[str]
    blocklist: list[str]
    clipboard_safe_mode: bool


@router.get("/policy", response_model=PrivacyPolicyConfigResponse)
async def get_privacy_policy(request: Request) -> PrivacyPolicyConfigResponse:
    service = _privacy_policy_config_service(request)
    try:
        return _policy_response(service.load())
    except PrivacyPolicyConfigError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.put("/policy", response_model=PrivacyPolicyConfigResponse)
async def update_privacy_policy(
    request_body: PrivacyPolicyConfigRequest,
    request: Request,
) -> PrivacyPolicyConfigResponse:
    service = _privacy_policy_config_service(request)
    try:
        saved = service.save(
            PrivacyPolicyConfig(
                allowlist=tuple(request_body.allowlist),
                blocklist=tuple(request_body.blocklist),
                clipboard_safe_mode=request_body.clipboard_safe_mode,
            )
        )
    except PrivacyPolicyConfigError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _policy_response(saved)


def _privacy_policy_config_service(request: Request) -> PrivacyPolicyConfigService:
    return cast(PrivacyPolicyConfigService, request.app.state.privacy_policy_config_service)


def _policy_response(config: PrivacyPolicyConfig) -> PrivacyPolicyConfigResponse:
    return PrivacyPolicyConfigResponse(
        allowlist=list(config.allowlist),
        blocklist=list(config.blocklist),
        clipboard_safe_mode=config.clipboard_safe_mode,
    )
