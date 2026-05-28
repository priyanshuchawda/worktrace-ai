from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from worktrace_agent.api.app import create_app
from worktrace_agent.capture.active_window import ActiveWindowSnapshot
from worktrace_agent.capture.screenshot_capture import ScreenshotProvider
from worktrace_agent.capture.screenshot_sampler import ScreenshotFrame
from worktrace_agent.privacy.config import PrivacyPolicyConfigService


class StaticActiveWindowProvider:
    def get_active_window(self) -> ActiveWindowSnapshot:
        return ActiveWindowSnapshot(
            app="VS Code",
            window_title="workaudit-ai - App.tsx",
            process_name="Code.exe",
            timestamp="2026-05-06T09:14:01+05:30",
            confidence=0.98,
        )


class StaticScreenshotProvider(ScreenshotProvider):
    def capture_frame(self, *, session_id: str, timestamp: str) -> ScreenshotFrame:
        return ScreenshotFrame(
            session_id=session_id,
            timestamp=timestamp,
            width=8,
            height=8,
            rgb_bytes=bytes([80, 80, 80]) * 8 * 8,
        )


def test_privacy_policy_config_loads_saves_and_normalizes(tmp_path: Path) -> None:
    config_path = tmp_path / "privacy-policy.json"
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            privacy_policy_config_service=PrivacyPolicyConfigService(config_path=config_path),
        )
    )

    default_response = client.get("/privacy/policy")
    update_response = client.put(
        "/privacy/policy",
        json={
            "allowlist": [" Code.exe ", "code.exe", ""],
            "blocklist": [" chrome.exe "],
            "clipboard_safe_mode": False,
        },
    )
    reloaded_client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            privacy_policy_config_service=PrivacyPolicyConfigService(config_path=config_path),
        )
    )

    assert default_response.status_code == 200
    assert default_response.json() == {
        "allowlist": [],
        "blocklist": [],
        "clipboard_safe_mode": True,
    }
    assert update_response.status_code == 200
    assert update_response.json() == {
        "allowlist": ["Code.exe"],
        "blocklist": ["chrome.exe"],
        "clipboard_safe_mode": False,
    }
    assert reloaded_client.get("/privacy/policy").json() == update_response.json()


def test_privacy_policy_rejects_sensitive_entries_without_leaking_value(tmp_path: Path) -> None:
    secret = "ghp_" + "test"
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            privacy_policy_config_service=PrivacyPolicyConfigService(
                config_path=tmp_path / "privacy-policy.json"
            ),
        )
    )

    response = client.put(
        "/privacy/policy",
        json={
            "allowlist": [f"Code.exe {secret}"],
            "blocklist": [],
            "clipboard_safe_mode": True,
        },
    )

    assert response.status_code == 400
    assert "contains sensitive text" in response.json()["detail"]
    assert secret not in str(response.json())


def test_persisted_blocklist_is_applied_to_capture_workers(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            active_window_provider=StaticActiveWindowProvider(),
            screenshot_provider=StaticScreenshotProvider(),
            privacy_policy_config_service=PrivacyPolicyConfigService(
                config_path=tmp_path / "privacy-policy.json"
            ),
            recorder_poll_interval_seconds=0.01,
            screenshot_interval_seconds=0.01,
        )
    )
    client.put(
        "/privacy/policy",
        json={
            "allowlist": [],
            "blocklist": ["Code.exe"],
            "clipboard_safe_mode": True,
        },
    )

    client.post(
        "/sessions/start",
        json={
            "session_id": "sess_api_privacy_policy_001",
            "started_at": "2026-05-06T09:14:00+05:30",
            "privacy_mode": "standard",
        },
    )
    client.post(
        "/sessions/sess_api_privacy_policy_001/stop",
        json={"stopped_at": "2026-05-06T09:15:00+05:30"},
    )

    assert client.get("/sessions/sess_api_privacy_policy_001/events").json()["events"] == []
    assert (
        client.get("/sessions/sess_api_privacy_policy_001/screenshots").json()["screenshots"] == []
    )


def test_private_mode_still_suppresses_capture_when_policy_allows_app(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            db_path=tmp_path / "worktrace.sqlite",
            active_window_provider=StaticActiveWindowProvider(),
            screenshot_provider=StaticScreenshotProvider(),
            privacy_policy_config_service=PrivacyPolicyConfigService(
                config_path=tmp_path / "privacy-policy.json"
            ),
            recorder_poll_interval_seconds=0.01,
            screenshot_interval_seconds=0.01,
        )
    )
    client.put(
        "/privacy/policy",
        json={
            "allowlist": ["Code.exe"],
            "blocklist": [],
            "clipboard_safe_mode": False,
        },
    )

    client.post(
        "/sessions/start",
        json={
            "session_id": "sess_api_privacy_policy_private",
            "started_at": "2026-05-06T09:14:00+05:30",
            "privacy_mode": "private",
        },
    )
    client.post(
        "/sessions/sess_api_privacy_policy_private/stop",
        json={"stopped_at": "2026-05-06T09:15:00+05:30"},
    )

    assert client.get("/sessions/sess_api_privacy_policy_private/events").json()["events"] == []
    assert (
        client.get("/sessions/sess_api_privacy_policy_private/screenshots").json()["screenshots"]
        == []
    )
