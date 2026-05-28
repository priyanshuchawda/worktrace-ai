from __future__ import annotations

from pathlib import Path

import pytest

from worktrace_agent.api.app import default_artifact_root, default_db_path


def test_python_module_entrypoint_imports_cleanly() -> None:
    import worktrace_agent.__main__ as entrypoint

    assert callable(entrypoint.main)


def test_sidecar_entrypoint_uses_local_host_and_configured_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import worktrace_agent.__main__ as entrypoint

    monkeypatch.setenv("WORKTRACE_SIDECAR_HOST", "127.0.0.1")
    monkeypatch.setenv("WORKTRACE_SIDECAR_PORT", "4567")

    config = entrypoint.read_sidecar_server_config()

    assert config.host == "127.0.0.1"
    assert config.port == 4567


def test_sidecar_entrypoint_rejects_non_local_host(monkeypatch: pytest.MonkeyPatch) -> None:
    import worktrace_agent.__main__ as entrypoint

    monkeypatch.setenv("WORKTRACE_SIDECAR_HOST", "0.0.0.0")
    monkeypatch.setenv("WORKTRACE_SIDECAR_PORT", "4567")

    with pytest.raises(SystemExit, match="WORKTRACE_SIDECAR_HOST must be 127.0.0.1"):
        entrypoint.read_sidecar_server_config()


def test_sidecar_entrypoint_loads_private_env_without_overriding_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import worktrace_agent.__main__ as entrypoint

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "WORKTRACE_AI_PROVIDER=gemini_gemma_dev",
                "WORKTRACE_ENABLE_DEV_CLOUD_AI=true",
                "GEMINI_API_KEY=AIza-test-secret-value-that-must-not-print",
                "WORKTRACE_SIDECAR_PORT=9999",
            ]
        ),
        encoding="utf-8",
    )
    child_dir = tmp_path / "services" / "local-agent"
    child_dir.mkdir(parents=True)
    monkeypatch.setenv("WORKTRACE_SIDECAR_PORT", "4567")

    loaded_path = entrypoint.load_local_env_file(start_dir=child_dir)

    assert loaded_path == env_file
    assert entrypoint.read_sidecar_server_config().port == 4567
    assert "AIza-test" not in repr(entrypoint.read_sidecar_server_config())


def test_default_db_path_respects_configured_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configured = tmp_path / "db" / "worktrace.sqlite"
    monkeypatch.setenv("WORKTRACE_DB_PATH", str(configured))

    assert default_db_path() == configured


def test_default_artifact_root_is_local_and_deterministic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WORKTRACE_DB_PATH", str(tmp_path / "db" / "worktrace.sqlite"))

    assert default_artifact_root("sess_packaged_001") == (
        tmp_path / "sessions" / "sess_packaged_001"
    )
