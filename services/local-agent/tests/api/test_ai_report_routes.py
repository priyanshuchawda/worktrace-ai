from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from worktrace_agent.ai.provider_config import AiProviderConfig, AiReportProvider
from worktrace_agent.api.app import create_app
from worktrace_agent.domain.raw_event import RawEvent


def test_ai_report_status_defaults_to_unavailable_without_runtime(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            ai_provider_config=local_ollama_config_for_unreachable_test_port(),
        )
    )

    response = client.get("/sessions/sess_ai_missing_runtime/ai-report/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "runtime_unavailable"
    assert payload["can_generate"] is False
    assert payload["report"] is None
    assert "Local Ollama is not reachable" in payload["message"]
    assert "gemma4:e2b" in payload["message"]


def test_ai_report_generate_fails_safely_without_runtime_and_keeps_session_data(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            ai_provider_config=local_ollama_config_for_unreachable_test_port(),
        )
    )
    save_stopped_session(client, "sess_ai_unavailable_001")
    before_events = client.get("/sessions/sess_ai_unavailable_001/events").json()["events"]

    response = client.post("/sessions/sess_ai_unavailable_001/ai-report/generate")
    after_events = client.get("/sessions/sess_ai_unavailable_001/events").json()["events"]

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "runtime_unavailable"
    assert payload["can_generate"] is False
    assert payload["report"] is None
    assert "Local Ollama is not reachable" in payload["message"]
    assert after_events == before_events


def test_ai_report_generate_returns_fake_evidence_cited_report(tmp_path: Path) -> None:
    fake_service = FakeAiReportService()
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            ai_report_service=fake_service,
        )
    )
    save_stopped_session(client, "sess_ai_success_001")

    response = client.post("/sessions/sess_ai_success_001/ai-report/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "complete"
    assert payload["message"] == "Local AI report generated."
    assert payload["model_name"] == "fake-local-report-model"
    assert payload["runtime_ms"] == 42
    assert payload["input_hash"] == "sha256:fake-input-hash"
    assert payload["evidence_ids"] == ["evt_ai_report_terminal"]
    assert payload["report"]["summary"]["text"] == "Tests were run from PowerShell."
    assert payload["report"]["summary"]["evidence_event_ids"] == ["evt_ai_report_terminal"]
    assert "full prompt" not in str(payload).lower()
    assert fake_service.generated_sessions == ["sess_ai_success_001"]


def test_ai_report_generate_runtime_error_returns_failed_safely(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            ai_report_service=FailingAiReportService(),
        )
    )
    save_stopped_session(client, "sess_ai_failed_001")

    response = client.post("/sessions/sess_ai_failed_001/ai-report/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed_safely"
    assert payload["can_generate"] is False
    assert payload["report"] is None
    assert "full prompt" not in str(payload).lower()
    assert "ghp_test" not in str(payload)


def test_ai_report_cancel_returns_cancelled_state(tmp_path: Path) -> None:
    fake_service = FakeAiReportService()
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            ai_report_service=fake_service,
        )
    )

    response = client.post("/sessions/sess_ai_cancel_001/ai-report/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["message"] == "Local AI report generation cancelled."


def save_stopped_session(client: TestClient, session_id: str) -> None:
    client.post(
        "/sessions/start",
        json={
            "session_id": session_id,
            "started_at": "2026-05-06T09:14:00+05:30",
            "title": "AI report route fixture",
        },
    )
    client.post(
        f"/sessions/{session_id}/terminal-events",
        json={
            "timestamp": "2026-05-06T09:14:30+05:30",
            "command": "uv run --python 3.13 pytest",
            "shell": "powershell",
            "exit_code": 0,
        },
    )
    client.post(
        f"/sessions/{session_id}/stop",
        json={"stopped_at": "2026-05-06T09:15:00+05:30"},
    )


class FakeAiReportService:
    def __init__(self) -> None:
        self.generated_sessions: list[str] = []

    def status(self, *, session_id: str) -> dict[str, object]:
        return {
            "status": "ready",
            "message": "Local AI report runtime is ready.",
            "can_generate": True,
            "report": None,
            "evidence_ids": [],
            "model_name": "fake-local-report-model",
            "model_version": "fake-v1",
            "runtime_ms": None,
            "input_hash": None,
            "generated_at": None,
        }

    def generate(self, *, session_id: str, events: list[RawEvent]) -> dict[str, object]:
        self.generated_sessions.append(session_id)
        return {
            "status": "complete",
            "message": "Local AI report generated.",
            "can_generate": True,
            "report": {
                "session_id": session_id,
                "session_title": "AI report route fixture",
                "summary": {
                    "text": "Tests were run from PowerShell.",
                    "evidence_event_ids": ["evt_ai_report_terminal"],
                },
                "timeline": [],
                "blockers": [],
                "repeated_actions": [],
                "important_files": [],
                "commands": [
                    {
                        "command": "uv run --python 3.13 pytest",
                        "evidence_event_ids": ["evt_ai_report_terminal"],
                    }
                ],
                "workflow_steps": [],
                "confidence": 0.7,
                "known_evidence_event_ids": ["evt_ai_report_terminal"],
            },
            "evidence_ids": ["evt_ai_report_terminal"],
            "model_name": "fake-local-report-model",
            "model_version": "fake-v1",
            "runtime_ms": 42,
            "input_hash": "sha256:fake-input-hash",
            "generated_at": "2026-05-06T09:15:10+05:30",
        }

    def cancel(self, *, session_id: str) -> dict[str, object]:
        return {
            "status": "cancelled",
            "message": "Local AI report generation cancelled.",
            "can_generate": True,
            "report": None,
            "evidence_ids": [],
            "model_name": "fake-local-report-model",
            "model_version": "fake-v1",
            "runtime_ms": None,
            "input_hash": None,
            "generated_at": None,
        }


class FailingAiReportService(FakeAiReportService):
    def generate(self, *, session_id: str, events: list[RawEvent]) -> dict[str, object]:
        raise RuntimeError("invalid JSON after retry; full prompt included ghp_test")


def local_ollama_config_for_unreachable_test_port() -> AiProviderConfig:
    return AiProviderConfig(
        provider=AiReportProvider.LOCAL_OLLAMA,
        dev_cloud_enabled=False,
        local_ollama_base_url="http://127.0.0.1:9",
    )
