from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from worktrace_agent.ai.model_cache import (
    ModelCacheStatus,
    ModelDownloadSpec,
    check_model_cache,
    default_model_cache_root,
    install_model_from_local_file,
    uninstall_model,
)

HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "llama_cpp",
    "ollama",
    "paddleocr",
    "faster_whisper",
)


def test_required_model_cache_states_are_explicit() -> None:
    assert {status.value for status in ModelCacheStatus} == {
        "not_installed",
        "downloading",
        "verifying",
        "installed",
        "loading",
        "ready",
        "unavailable",
        "too_slow",
        "failed",
    }


def test_model_download_spec_accepts_source_url_and_manual_install_instructions() -> None:
    spec = ModelDownloadSpec(
        model_id="report/fake-report",
        filename="fake-report.gguf",
        expected_bytes=10,
        sha256=None,
        source_url="https://example.test/fake-report.gguf",
        manual_install_instructions="Download the model manually and select the file.",
    )

    state = check_model_cache(
        spec,
        cache_root=Path("cache"),
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )

    assert state.status is ModelCacheStatus.NOT_INSTALLED


def test_model_download_spec_rejects_source_url_credentials() -> None:
    spec = ModelDownloadSpec(
        model_id="report/fake-report",
        filename="fake-report.gguf",
        expected_bytes=10,
        sha256=None,
        source_url="https://user:secret@example.test/fake-report.gguf",
    )

    with pytest.raises(ValueError, match="credentials"):
        check_model_cache(
            spec,
            cache_root=Path("cache"),
            disk_space=FakeDiskSpace(free_bytes=1_000),
        )


def test_default_model_cache_root_prefers_explicit_env_then_local_app_data(
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "explicit-model-cache"
    local_app_data = tmp_path / "LocalAppData"

    assert default_model_cache_root({"WORKTRACE_MODEL_CACHE": str(explicit)}) == explicit
    assert default_model_cache_root({"LOCALAPPDATA": str(local_app_data)}) == (
        local_app_data / "WorkTrace" / "models"
    )


def test_default_model_cache_root_falls_back_to_home(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert default_model_cache_root({}) == tmp_path / ".worktrace" / "models"


def test_missing_model_with_enough_disk_is_not_installed_and_download_allowed(
    tmp_path: Path,
) -> None:
    spec = model_spec(expected_bytes=100, sha256=None)

    state = check_model_cache(
        spec,
        cache_root=tmp_path,
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )

    assert state.status is ModelCacheStatus.NOT_INSTALLED
    assert state.can_download is True
    assert state.path == tmp_path / "report" / "fake-report" / "fake-report.gguf"
    assert state.expected_bytes == 100
    assert state.actual_bytes is None
    assert state.user_message == "Model is not installed. Download can be offered explicitly."


def test_missing_model_with_insufficient_disk_fails_safely(tmp_path: Path) -> None:
    spec = model_spec(expected_bytes=1_000, sha256=None)

    state = check_model_cache(
        spec,
        cache_root=tmp_path,
        disk_space=FakeDiskSpace(free_bytes=500),
    )

    assert state.status is ModelCacheStatus.FAILED
    assert state.can_download is False
    assert "Not enough disk space" in state.user_message
    assert state.path.exists() is False


def test_installed_model_with_matching_hash_is_installed(tmp_path: Path) -> None:
    model_path = tmp_path / "report" / "fake-report" / "fake-report.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"fake model")
    spec = model_spec(
        expected_bytes=model_path.stat().st_size,
        sha256="1eec943f3fbf69947176e7c711415ad88a08184169f72cd31dca0ab071e14939",
    )

    state = check_model_cache(
        spec,
        cache_root=tmp_path,
        disk_space=FakeDiskSpace(free_bytes=0),
    )

    assert state.status is ModelCacheStatus.INSTALLED
    assert state.can_download is False
    assert state.actual_bytes == len(b"fake model")
    assert state.user_message == "Model is installed in the local cache."


def test_installed_model_with_hash_mismatch_fails_without_deleting_file(tmp_path: Path) -> None:
    model_path = tmp_path / "report" / "fake-report" / "fake-report.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"tampered")

    state = check_model_cache(
        model_spec(expected_bytes=8, sha256="0" * 64),
        cache_root=tmp_path,
        disk_space=FakeDiskSpace(free_bytes=0),
    )

    assert state.status is ModelCacheStatus.FAILED
    assert state.can_download is False
    assert "checksum" in state.user_message.lower()
    assert model_path.read_bytes() == b"tampered"


def test_local_file_install_fails_when_disk_space_is_insufficient(tmp_path: Path) -> None:
    source_path = tmp_path / "source.gguf"
    source_path.write_bytes(b"fake model")
    cache_root = tmp_path / "models"

    state = install_model_from_local_file(
        model_spec(expected_bytes=len(b"fake model"), sha256=None),
        source_path=source_path,
        cache_root=cache_root,
        disk_space=FakeDiskSpace(free_bytes=1),
    )

    assert state.status is ModelCacheStatus.FAILED
    assert state.can_download is False
    assert "Not enough disk space" in state.user_message
    assert (cache_root / "report" / "fake-report" / "fake-report.gguf").exists() is False


def test_local_file_install_checksum_mismatch_preserves_existing_target(
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "models"
    model_path = cache_root / "report" / "fake-report" / "fake-report.gguf"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"existing model")
    source_path = tmp_path / "source.gguf"
    source_path.write_bytes(b"new model")

    state = install_model_from_local_file(
        model_spec(expected_bytes=len(b"new model"), sha256="0" * 64),
        source_path=source_path,
        cache_root=cache_root,
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )

    assert state.status is ModelCacheStatus.FAILED
    assert "checksum" in state.user_message.lower()
    assert model_path.read_bytes() == b"existing model"
    assert not list(model_path.parent.glob("*.tmp"))


def test_local_file_install_success_copies_to_cache_path(tmp_path: Path) -> None:
    source_path = tmp_path / "source.gguf"
    source_path.write_bytes(b"fake model")
    cache_root = tmp_path / "models"

    state = install_model_from_local_file(
        model_spec(
            expected_bytes=len(b"fake model"),
            sha256="1eec943f3fbf69947176e7c711415ad88a08184169f72cd31dca0ab071e14939",
        ),
        source_path=source_path,
        cache_root=cache_root,
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )

    assert state.status is ModelCacheStatus.INSTALLED
    assert state.path == cache_root / "report" / "fake-report" / "fake-report.gguf"
    assert state.path.read_bytes() == b"fake model"
    assert state.actual_bytes == len(b"fake model")


def test_uninstall_model_deletes_only_exact_cached_model_file(tmp_path: Path) -> None:
    cache_root = tmp_path / "models"
    model_path = cache_root / "report" / "fake-report" / "fake-report.gguf"
    sibling_path = model_path.parent / "keep.txt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"fake model")
    sibling_path.write_text("keep", encoding="utf-8")

    state = uninstall_model(model_spec(expected_bytes=10, sha256=None), cache_root=cache_root)

    assert state.status is ModelCacheStatus.NOT_INSTALLED
    assert state.path == model_path
    assert model_path.exists() is False
    assert sibling_path.read_text(encoding="utf-8") == "keep"


def test_gitignore_keeps_common_model_artifacts_out_of_git() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")

    for pattern in ("models/", "*.gguf", "*.safetensors", "*.onnx", "*.tflite", "*.task", "*.bin"):
        assert pattern in gitignore


def test_model_cache_checks_do_not_import_heavy_model_modules(tmp_path: Path) -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    check_model_cache(
        model_spec(expected_bytes=100, sha256=None),
        cache_root=tmp_path,
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )
    source_path = tmp_path / "source.gguf"
    source_path.write_bytes(b"fake model")
    install_model_from_local_file(
        model_spec(expected_bytes=len(b"fake model"), sha256=None),
        source_path=source_path,
        cache_root=tmp_path / "models",
        disk_space=FakeDiskSpace(free_bytes=1_000),
    )
    uninstall_model(
        model_spec(expected_bytes=len(b"fake model"), sha256=None),
        cache_root=tmp_path / "models",
    )

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)


def model_spec(*, expected_bytes: int, sha256: str | None) -> ModelDownloadSpec:
    return ModelDownloadSpec(
        model_id="report/fake-report",
        filename="fake-report.gguf",
        expected_bytes=expected_bytes,
        sha256=sha256,
    )


class FakeDiskSpace:
    def __init__(self, *, free_bytes: int) -> None:
        self.free_bytes = free_bytes

    def free_bytes_for(self, path: Path) -> int:
        return self.free_bytes
