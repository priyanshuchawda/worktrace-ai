from __future__ import annotations

import sqlite3
from typing import cast

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from worktrace_agent.api.ai_report_service import (
    AiReportService,
    failed_ai_report_result,
    safe_ai_report_result,
)
from worktrace_agent.api.session_recorder_service import (
    ScreenshotPreview,
    SessionDeletionResult,
    SessionExportPreview,
    SessionRecorderService,
    SessionSummary,
    is_sqlite_missing_session_error,
    map_session_error,
)
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.db.session_state_repository import SessionTransitionError
from worktrace_agent.domain.raw_event import RawEvent
from worktrace_agent.domain.session_state import SessionRecord

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    title: str | None = None
    goal: str | None = None
    project_label: str | None = None
    tags: list[str] = Field(default_factory=list)
    storage_path: str | None = None
    privacy_mode: str = Field(default="standard", min_length=1)
    file_watch_roots: list[str] = Field(default_factory=list)


class StopSessionRequest(BaseModel):
    stopped_at: str = Field(min_length=1)


class PauseSessionRequest(BaseModel):
    paused_at: str = Field(min_length=1)


class ResumeSessionRequest(BaseModel):
    resumed_at: str = Field(min_length=1)
    file_watch_roots: list[str] = Field(default_factory=list)


class TerminalCommandEventRequest(BaseModel):
    timestamp: str = Field(min_length=1)
    command: str = Field(min_length=1)
    shell: str = Field(default="powershell", min_length=1)
    exit_code: int | None = None


class SessionResponse(BaseModel):
    id: str
    started_at: str
    ended_at: str | None
    status: str
    title: str | None
    goal: str | None
    project_label: str | None
    tags: list[str]
    storage_path: str | None
    privacy_mode: str


class RawEventResponse(BaseModel):
    id: str
    session_id: str
    timestamp: str
    source: str
    type: str
    privacy_level: str
    confidence: float
    metadata: dict[str, object]


class SessionEventsResponse(BaseModel):
    events: list[RawEventResponse]


class SessionSummaryResponse(BaseModel):
    id: str
    started_at: str
    ended_at: str | None
    status: str
    title: str | None
    goal: str | None
    project_label: str | None
    tags: list[str]
    storage_path: str | None
    privacy_mode: str
    event_count: int
    screenshot_count: int


class SessionsResponse(BaseModel):
    sessions: list[SessionSummaryResponse]


class ScreenshotResponse(BaseModel):
    id: str
    session_id: str
    source_event_id: str | None
    timestamp: str
    width: int
    height: int
    stored_width: int
    stored_height: int
    byte_size: int
    content_hash: str
    visual_hash: str
    storage_path: str


class SessionScreenshotsResponse(BaseModel):
    screenshots: list[ScreenshotResponse]


class ScreenshotPreviewResponse(BaseModel):
    screenshot_id: str
    image_data_url: str
    ocr_snippets: list[str]


class DeleteScreenshotsResponse(BaseModel):
    deleted_files: int
    missing_files: int
    deleted_rows: int


class SessionExportResponse(BaseModel):
    format: str
    path: str
    preview: str
    evidence_ids: list[str]


class SessionFolderResponse(BaseModel):
    path: str


class DeleteSessionResponse(BaseModel):
    deleted_session_rows: int
    deleted_screenshot_files: int
    missing_screenshot_files: int
    deleted_screenshot_rows: int
    removed_artifact_root: bool


class AiReportResponse(BaseModel):
    status: str
    message: str
    can_generate: bool
    report: dict[str, object] | None
    evidence_ids: list[str]
    model_name: str | None
    model_version: str | None
    provider: str | None
    requested_model: str | None
    actual_model: str | None
    fallback_used: bool
    runtime_ms: int | None
    input_hash: str | None
    generated_at: str | None


@router.get("", response_model=SessionsResponse)
async def list_recording_sessions(request: Request) -> SessionsResponse:
    service = _session_service(request)
    return SessionsResponse(
        sessions=[_session_summary_response(session) for session in service.list_sessions()]
    )


@router.post("/start", response_model=SessionResponse)
async def start_recording_session(
    request_body: StartSessionRequest,
    request: Request,
) -> SessionResponse:
    service = _session_service(request)
    try:
        session = await service.start_recording_session(
            session_id=request_body.session_id,
            started_at=request_body.started_at,
            title=request_body.title,
            goal=request_body.goal,
            project_label=request_body.project_label,
            tags=request_body.tags,
            storage_path=request_body.storage_path,
            privacy_mode=request_body.privacy_mode,
            file_watch_roots=request_body.file_watch_roots,
        )
    except SessionTransitionError as error:
        status_code, detail = map_session_error(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    return _session_response(session)


@router.post("/{session_id}/pause", response_model=SessionResponse)
async def pause_recording_session(
    session_id: str,
    request_body: PauseSessionRequest,
    request: Request,
) -> SessionResponse:
    service = _session_service(request)
    try:
        session = await service.pause_recording_session(
            session_id=session_id,
            paused_at=request_body.paused_at,
        )
    except SessionTransitionError as error:
        status_code, detail = map_session_error(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    return _session_response(session)


@router.post("/{session_id}/resume", response_model=SessionResponse)
async def resume_recording_session(
    session_id: str,
    request_body: ResumeSessionRequest,
    request: Request,
) -> SessionResponse:
    service = _session_service(request)
    try:
        session = await service.resume_recording_session(
            session_id=session_id,
            resumed_at=request_body.resumed_at,
            file_watch_roots=request_body.file_watch_roots,
        )
    except SessionTransitionError as error:
        status_code, detail = map_session_error(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    return _session_response(session)


@router.post("/{session_id}/stop", response_model=SessionResponse)
async def stop_recording_session(
    session_id: str,
    request_body: StopSessionRequest,
    request: Request,
) -> SessionResponse:
    service = _session_service(request)
    try:
        session = await service.stop_recording_session(
            session_id=session_id,
            stopped_at=request_body.stopped_at,
        )
    except SessionTransitionError as error:
        status_code, detail = map_session_error(error)
        raise HTTPException(status_code=status_code, detail=detail) from error
    return _session_response(session)


@router.get("/{session_id}/events", response_model=SessionEventsResponse)
async def list_recording_session_events(session_id: str, request: Request) -> SessionEventsResponse:
    service = _session_service(request)
    return SessionEventsResponse(
        events=[
            _raw_event_response(event)
            for event in service.list_session_events(session_id=session_id)
        ]
    )


@router.post("/{session_id}/terminal-events", response_model=RawEventResponse)
async def ingest_terminal_command_event(
    session_id: str,
    request_body: TerminalCommandEventRequest,
    request: Request,
) -> RawEventResponse:
    service = _session_service(request)
    try:
        event = service.ingest_terminal_command(
            session_id=session_id,
            timestamp=request_body.timestamp,
            command=request_body.command,
            shell=request_body.shell,  # nosec B604
            exit_code=request_body.exit_code,
        )
    except sqlite3.Error as error:
        if is_sqlite_missing_session_error(error):
            raise HTTPException(status_code=409, detail=f"Unknown session: {session_id}") from error
        raise HTTPException(status_code=500, detail="Could not ingest terminal event.") from error
    return _raw_event_response(event)


@router.get("/{session_id}/screenshots", response_model=SessionScreenshotsResponse)
async def list_recording_session_screenshots(
    session_id: str,
    request: Request,
) -> SessionScreenshotsResponse:
    service = _session_service(request)
    return SessionScreenshotsResponse(
        screenshots=[
            _screenshot_response(screenshot)
            for screenshot in service.list_session_screenshots(session_id=session_id)
        ]
    )


@router.get(
    "/{session_id}/screenshots/{screenshot_id}/preview",
    response_model=ScreenshotPreviewResponse,
)
async def get_recording_session_screenshot_preview(
    session_id: str,
    screenshot_id: str,
    request: Request,
) -> ScreenshotPreviewResponse:
    service = _session_service(request)
    try:
        preview = service.screenshot_preview(session_id=session_id, screenshot_id=screenshot_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _screenshot_preview_response(preview)


@router.delete("/{session_id}/screenshots", response_model=DeleteScreenshotsResponse)
async def delete_recording_session_screenshots(
    session_id: str,
    request: Request,
) -> DeleteScreenshotsResponse:
    service = _session_service(request)
    result = service.delete_session_screenshots(session_id=session_id)
    return DeleteScreenshotsResponse(
        deleted_files=result.deleted_files,
        missing_files=result.missing_files,
        deleted_rows=result.deleted_rows,
    )


@router.post("/{session_id}/exports/markdown", response_model=SessionExportResponse)
async def export_recording_session_markdown(
    session_id: str,
    request: Request,
) -> SessionExportResponse:
    service = _session_service(request)
    try:
        export = service.export_session_markdown_preview(session_id=session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _session_export_response(export)


@router.post("/{session_id}/exports/raw-json", response_model=SessionExportResponse)
async def export_recording_session_raw_json(
    session_id: str,
    request: Request,
) -> SessionExportResponse:
    service = _session_service(request)
    try:
        export = service.export_session_raw_json_preview(session_id=session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _session_export_response(export)


@router.get("/{session_id}/ai-report/status", response_model=AiReportResponse)
async def get_ai_report_status(session_id: str, request: Request) -> AiReportResponse:
    service = _ai_report_service(request)
    try:
        result = service.status(session_id=session_id)
    except Exception:
        result = failed_ai_report_result()
    return AiReportResponse.model_validate(safe_ai_report_result(result))


@router.post("/{session_id}/ai-report/generate", response_model=AiReportResponse)
async def generate_ai_report(session_id: str, request: Request) -> AiReportResponse:
    session_service = _session_service(request)
    service = _ai_report_service(request)
    events = session_service.list_session_events(session_id=session_id)
    try:
        result = service.generate(session_id=session_id, events=events)
    except Exception:
        result = failed_ai_report_result()
    return AiReportResponse.model_validate(safe_ai_report_result(result))


@router.post("/{session_id}/ai-report/cancel", response_model=AiReportResponse)
async def cancel_ai_report(session_id: str, request: Request) -> AiReportResponse:
    service = _ai_report_service(request)
    try:
        result = service.cancel(session_id=session_id)
    except Exception:
        result = failed_ai_report_result()
    return AiReportResponse.model_validate(safe_ai_report_result(result))


@router.get("/{session_id}/folder", response_model=SessionFolderResponse)
async def get_recording_session_folder(
    session_id: str,
    request: Request,
) -> SessionFolderResponse:
    service = _session_service(request)
    try:
        folder = service.session_folder(session_id=session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return SessionFolderResponse(path=folder.path.as_posix())


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_recording_session(
    session_id: str,
    request: Request,
) -> DeleteSessionResponse:
    service = _session_service(request)
    try:
        result = await service.delete_session(session_id=session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _delete_session_response(result)


def _session_service(request: Request) -> SessionRecorderService:
    return cast(SessionRecorderService, request.app.state.session_recorder_service)


def _ai_report_service(request: Request) -> AiReportService:
    return cast(AiReportService, request.app.state.ai_report_service)


def _session_response(session: SessionRecord) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status.value,
        title=session.title,
        goal=session.goal,
        project_label=session.project_label,
        tags=list(session.tags),
        storage_path=session.storage_path,
        privacy_mode=session.privacy_mode,
    )


def _raw_event_response(event: RawEvent) -> RawEventResponse:
    return RawEventResponse(
        id=event.id,
        session_id=event.session_id,
        timestamp=event.timestamp,
        source=event.source,
        type=event.type,
        privacy_level=event.privacy_level,
        confidence=event.confidence,
        metadata=event.metadata,
    )


def _session_summary_response(session: SessionSummary) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        title=session.title,
        goal=session.goal,
        project_label=session.project_label,
        tags=session.tags,
        storage_path=session.storage_path,
        privacy_mode=session.privacy_mode,
        event_count=session.event_count,
        screenshot_count=session.screenshot_count,
    )


def _screenshot_response(screenshot: ScreenshotArtifact) -> ScreenshotResponse:
    return ScreenshotResponse(
        id=screenshot.id,
        session_id=screenshot.session_id,
        source_event_id=screenshot.source_event_id,
        timestamp=screenshot.timestamp,
        width=screenshot.width,
        height=screenshot.height,
        stored_width=screenshot.stored_width,
        stored_height=screenshot.stored_height,
        byte_size=screenshot.byte_size,
        content_hash=screenshot.content_hash,
        visual_hash=screenshot.visual_hash,
        storage_path=screenshot.storage_path,
    )


def _screenshot_preview_response(preview: ScreenshotPreview) -> ScreenshotPreviewResponse:
    return ScreenshotPreviewResponse(
        screenshot_id=preview.screenshot_id,
        image_data_url=preview.image_data_url,
        ocr_snippets=preview.ocr_snippets,
    )


def _session_export_response(export: SessionExportPreview) -> SessionExportResponse:
    return SessionExportResponse(
        format=export.format,
        path=export.path.as_posix(),
        preview=export.preview,
        evidence_ids=export.evidence_ids,
    )


def _delete_session_response(result: SessionDeletionResult) -> DeleteSessionResponse:
    return DeleteSessionResponse(
        deleted_session_rows=result.deleted_session_rows,
        deleted_screenshot_files=result.deleted_screenshot_files,
        missing_screenshot_files=result.missing_screenshot_files,
        deleted_screenshot_rows=result.deleted_screenshot_rows,
        removed_artifact_root=result.removed_artifact_root,
    )
