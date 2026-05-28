from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime
from typing import Protocol, cast

from pydantic import ValidationError

from worktrace_agent.ai.gemma_manifest import (
    DEFAULT_GEMMA_REPORT_MODEL,
    build_gemma_report_runtime_config,
)
from worktrace_agent.ai.local_http import require_local_http_url
from worktrace_agent.ai.local_report_runtime import (
    LocalReportRuntimeConfig,
    LocalReportRuntimeError,
    OllamaReportModel,
)
from worktrace_agent.ai.provider_config import AiProviderConfig
from worktrace_agent.ai.reporting import (
    EvidenceCitedReport,
    HallucinationGuardError,
    LocalReportModel,
    ReportGenerationError,
    generate_evidence_cited_report,
)
from worktrace_agent.api.ai_report_service import failed_ai_report_result
from worktrace_agent.domain.raw_event import RawEvent
from worktrace_agent.timeline.deterministic import build_deterministic_timeline

ReportModelFactory = Callable[[LocalReportRuntimeConfig], LocalReportModel]


class OllamaModelLister(Protocol):
    def list_model_names(self, *, base_url: str, timeout_seconds: int) -> tuple[str, ...]:
        """Return installed Ollama model names from a localhost runtime."""
        ...


class OllamaApiModelLister:
    def list_model_names(self, *, base_url: str, timeout_seconds: int) -> tuple[str, ...]:
        tags_url = require_local_http_url(f"{base_url.rstrip('/')}/api/tags")
        request = urllib.request.Request(tags_url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise LocalReportRuntimeError("Local Ollama runtime is not reachable.") from error
        if not isinstance(payload, dict):
            raise LocalReportRuntimeError("Local Ollama model list is invalid.")
        response_payload = cast(dict[str, object], payload)
        models = response_payload.get("models")
        if not isinstance(models, list):
            raise LocalReportRuntimeError("Local Ollama model list is invalid.")
        model_entries = cast(list[object], models)
        names: list[str] = []
        for item in model_entries:
            if not isinstance(item, dict):
                continue
            model_item = cast(dict[str, object], item)
            name = model_item.get("name") or model_item.get("model")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return tuple(names)


class LocalOllamaReportService:
    def __init__(
        self,
        *,
        config: AiProviderConfig,
        model_lister: OllamaModelLister | None = None,
        report_model_factory: ReportModelFactory | None = None,
    ) -> None:
        self._config = config
        self._manifest = DEFAULT_GEMMA_REPORT_MODEL
        self._model_lister = model_lister or OllamaApiModelLister()
        self._report_model_factory = report_model_factory or _build_ollama_report_model

    def status(self, *, session_id: str) -> dict[str, object]:
        return self._status_result()

    def generate(self, *, session_id: str, events: list[RawEvent]) -> dict[str, object]:
        availability = self._availability()
        if availability is not None:
            return availability
        started = time.perf_counter()
        try:
            runtime_config = build_gemma_report_runtime_config(
                base_url=self._config.local_ollama_base_url,
                manifest=self._manifest,
            )
            model = self._report_model_factory(runtime_config)
            report = generate_evidence_cited_report(
                session={"id": session_id, "title": "WorkTrace session", "status": "stopped"},
                timeline=build_deterministic_timeline(events),
                model=model,
                model_name=self._manifest.ollama_model,
                model_version=self._manifest.key,
                generated_at=_generated_at(),
            )
            return {
                "status": "complete",
                "message": "Local Ollama AI report generated.",
                "can_generate": True,
                "report": report.model_dump(mode="json"),
                "evidence_ids": _report_evidence_ids(report),
                "model_name": self._manifest.ollama_model,
                "model_version": self._manifest.key,
                "provider": self._config.provider.value,
                "requested_model": self._manifest.ollama_model,
                "actual_model": self._manifest.ollama_model,
                "fallback_used": False,
                "runtime_ms": _runtime_ms(started),
                "input_hash": report.model_metadata.input_hash,
                "generated_at": report.model_metadata.generated_at,
            }
        except (
            HallucinationGuardError,
            LocalReportRuntimeError,
            ReportGenerationError,
            ValidationError,
            ValueError,
        ):
            return {
                **failed_ai_report_result(),
                "provider": self._config.provider.value,
                "requested_model": self._manifest.ollama_model,
                "actual_model": None,
                "fallback_used": False,
            }

    def cancel(self, *, session_id: str) -> dict[str, object]:
        return {
            "status": "cancelled",
            "message": "Local Ollama AI report generation cancelled.",
            "can_generate": True,
            "report": None,
            "evidence_ids": [],
            "model_name": self._manifest.ollama_model,
            "model_version": self._manifest.key,
            "provider": self._config.provider.value,
            "requested_model": self._manifest.ollama_model,
            "actual_model": None,
            "fallback_used": False,
            "runtime_ms": None,
            "input_hash": None,
            "generated_at": None,
        }

    def _status_result(self) -> dict[str, object]:
        availability = self._availability()
        if availability is not None:
            return availability
        return {
            "status": "ready",
            "message": f"Local Ollama report runtime is ready with {self._manifest.ollama_model}.",
            "can_generate": True,
            "report": None,
            "evidence_ids": [],
            "model_name": self._manifest.ollama_model,
            "model_version": self._manifest.key,
            "provider": self._config.provider.value,
            "requested_model": self._manifest.ollama_model,
            "actual_model": None,
            "fallback_used": False,
            "runtime_ms": None,
            "input_hash": None,
            "generated_at": None,
        }

    def _availability(self) -> dict[str, object] | None:
        try:
            installed_models = self._model_lister.list_model_names(
                base_url=self._config.local_ollama_base_url,
                timeout_seconds=3,
            )
        except LocalReportRuntimeError:
            return self._unavailable_result(
                f"Local Ollama is not reachable at {self._config.local_ollama_base_url}. "
                f"Start Ollama and install {self._manifest.ollama_model} before generating reports."
            )
        if self._manifest.ollama_model not in installed_models:
            return self._unavailable_result(
                f"Local Ollama is reachable, but {self._manifest.ollama_model} is not installed. "
                "Install the model in Ollama before generating reports."
            )
        return None

    def _unavailable_result(self, message: str) -> dict[str, object]:
        return {
            "status": "runtime_unavailable",
            "message": message,
            "can_generate": False,
            "report": None,
            "evidence_ids": [],
            "model_name": self._manifest.ollama_model,
            "model_version": self._manifest.key,
            "provider": self._config.provider.value,
            "requested_model": self._manifest.ollama_model,
            "actual_model": None,
            "fallback_used": False,
            "runtime_ms": None,
            "input_hash": None,
            "generated_at": None,
        }


def _build_ollama_report_model(config: LocalReportRuntimeConfig) -> LocalReportModel:
    return OllamaReportModel(config=config)


def _report_evidence_ids(report: EvidenceCitedReport) -> list[str]:
    ordered_ids: list[str] = []
    for claim in report.all_claims():
        for evidence_id in claim.evidence_event_ids:
            if evidence_id not in ordered_ids:
                ordered_ids.append(evidence_id)
    return ordered_ids


def _generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _runtime_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
