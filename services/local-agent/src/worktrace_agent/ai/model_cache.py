from __future__ import annotations

import hashlib
import os
import shutil
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from worktrace_agent.privacy.redaction import redact_text

DEFAULT_DISK_SAFETY_MARGIN_BYTES = 0


class ModelCacheStatus(StrEnum):
    NOT_INSTALLED = "not_installed"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLED = "installed"
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    TOO_SLOW = "too_slow"
    FAILED = "failed"


class DiskSpaceProvider(Protocol):
    def free_bytes_for(self, path: Path) -> int:
        """Return available bytes for the filesystem containing path."""
        ...


@dataclass(frozen=True)
class ModelDownloadSpec:
    model_id: str
    filename: str
    expected_bytes: int
    sha256: str | None = None
    source_url: str | None = None
    manual_install_instructions: str | None = None


@dataclass(frozen=True)
class ModelCacheState:
    model_id: str
    status: ModelCacheStatus
    path: Path
    expected_bytes: int
    actual_bytes: int | None
    can_download: bool
    user_message: str


def default_model_cache_root(env: Mapping[str, str]) -> Path:
    configured = env.get("WORKTRACE_MODEL_CACHE")
    if configured and configured.strip():
        return Path(configured)

    local_app_data = env.get("LOCALAPPDATA")
    if local_app_data and local_app_data.strip():
        return Path(local_app_data) / "WorkTrace" / "models"

    return Path.home() / ".worktrace" / "models"


def check_model_cache(
    spec: ModelDownloadSpec,
    *,
    cache_root: Path,
    disk_space: DiskSpaceProvider,
    disk_safety_margin_bytes: int = DEFAULT_DISK_SAFETY_MARGIN_BYTES,
) -> ModelCacheState:
    _validate_spec(spec)
    if disk_safety_margin_bytes < 0:
        raise ValueError("disk_safety_margin_bytes must not be negative")

    model_path = _model_path(cache_root=cache_root, spec=spec)
    if model_path.exists():
        return _installed_state(spec=spec, model_path=model_path)

    free_bytes = disk_space.free_bytes_for(cache_root)
    required_bytes = spec.expected_bytes + disk_safety_margin_bytes
    if free_bytes < required_bytes:
        return ModelCacheState(
            model_id=redact_text(spec.model_id),
            status=ModelCacheStatus.FAILED,
            path=model_path,
            expected_bytes=spec.expected_bytes,
            actual_bytes=None,
            can_download=False,
            user_message=(
                "Not enough disk space for this model. "
                f"Required {required_bytes} bytes including safety margin."
            ),
        )

    return ModelCacheState(
        model_id=redact_text(spec.model_id),
        status=ModelCacheStatus.NOT_INSTALLED,
        path=model_path,
        expected_bytes=spec.expected_bytes,
        actual_bytes=None,
        can_download=True,
        user_message="Model is not installed. Download can be offered explicitly.",
    )


def install_model_from_local_file(
    spec: ModelDownloadSpec,
    *,
    source_path: Path,
    cache_root: Path,
    disk_space: DiskSpaceProvider,
    disk_safety_margin_bytes: int = DEFAULT_DISK_SAFETY_MARGIN_BYTES,
) -> ModelCacheState:
    _validate_spec(spec)
    if disk_safety_margin_bytes < 0:
        raise ValueError("disk_safety_margin_bytes must not be negative")

    target_path = _model_path(cache_root=cache_root, spec=spec)
    if not source_path.is_file():
        return _failed_state(
            spec=spec,
            path=target_path,
            actual_bytes=None,
            user_message="Selected model source file is unavailable.",
        )

    source_bytes = source_path.stat().st_size
    required_bytes = source_bytes + disk_safety_margin_bytes
    if disk_space.free_bytes_for(cache_root) < required_bytes:
        return _failed_state(
            spec=spec,
            path=target_path,
            actual_bytes=None,
            user_message=(
                "Not enough disk space for this model. "
                f"Required {required_bytes} bytes including safety margin."
            ),
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
    try:
        if temp_path.exists():
            temp_path.unlink()
        with source_path.open("rb") as source_file, temp_path.open("wb") as temp_file:
            shutil.copyfileobj(source_file, temp_file, length=1024 * 1024)

        actual_bytes = temp_path.stat().st_size
        if actual_bytes != spec.expected_bytes:
            temp_path.unlink(missing_ok=True)
            return _failed_state(
                spec=spec,
                path=target_path,
                actual_bytes=actual_bytes,
                user_message="Selected model file size does not match the manifest.",
            )
        if spec.sha256 is not None and _sha256(temp_path) != spec.sha256.lower():
            temp_path.unlink(missing_ok=True)
            return _failed_state(
                spec=spec,
                path=target_path,
                actual_bytes=actual_bytes,
                user_message="Selected model checksum does not match the manifest.",
            )

        os.replace(temp_path, target_path)
    except OSError:
        temp_path.unlink(missing_ok=True)
        return _failed_state(
            spec=spec,
            path=target_path,
            actual_bytes=None,
            user_message="Model install failed safely while writing the local cache.",
        )

    return _installed_state(spec=spec, model_path=target_path)


def uninstall_model(
    spec: ModelDownloadSpec,
    *,
    cache_root: Path,
) -> ModelCacheState:
    _validate_spec(spec)
    target_path = _model_path(cache_root=cache_root, spec=spec)
    if not target_path.exists():
        return _not_installed_state(
            spec=spec,
            path=target_path,
            user_message="Model is not installed.",
        )
    if not target_path.is_file():
        return _failed_state(
            spec=spec,
            path=target_path,
            actual_bytes=None,
            user_message="Model cache path exists but is not a file.",
        )

    actual_bytes = target_path.stat().st_size
    try:
        target_path.unlink()
    except OSError:
        return _failed_state(
            spec=spec,
            path=target_path,
            actual_bytes=actual_bytes,
            user_message="Model uninstall failed safely.",
        )

    return _not_installed_state(
        spec=spec,
        path=target_path,
        user_message="Model has been uninstalled from the local cache.",
    )


def _installed_state(*, spec: ModelDownloadSpec, model_path: Path) -> ModelCacheState:
    if not model_path.is_file():
        return ModelCacheState(
            model_id=redact_text(spec.model_id),
            status=ModelCacheStatus.FAILED,
            path=model_path,
            expected_bytes=spec.expected_bytes,
            actual_bytes=None,
            can_download=False,
            user_message="Model cache path exists but is not a file.",
        )

    actual_bytes = model_path.stat().st_size
    if spec.sha256 is not None and _sha256(model_path) != spec.sha256.lower():
        return ModelCacheState(
            model_id=redact_text(spec.model_id),
            status=ModelCacheStatus.FAILED,
            path=model_path,
            expected_bytes=spec.expected_bytes,
            actual_bytes=actual_bytes,
            can_download=False,
            user_message="Installed model checksum does not match the manifest.",
        )

    return ModelCacheState(
        model_id=redact_text(spec.model_id),
        status=ModelCacheStatus.INSTALLED,
        path=model_path,
        expected_bytes=spec.expected_bytes,
        actual_bytes=actual_bytes,
        can_download=False,
        user_message="Model is installed in the local cache.",
    )


def _failed_state(
    *,
    spec: ModelDownloadSpec,
    path: Path,
    actual_bytes: int | None,
    user_message: str,
) -> ModelCacheState:
    return ModelCacheState(
        model_id=redact_text(spec.model_id),
        status=ModelCacheStatus.FAILED,
        path=path,
        expected_bytes=spec.expected_bytes,
        actual_bytes=actual_bytes,
        can_download=False,
        user_message=redact_text(user_message),
    )


def _not_installed_state(
    *,
    spec: ModelDownloadSpec,
    path: Path,
    user_message: str,
) -> ModelCacheState:
    return ModelCacheState(
        model_id=redact_text(spec.model_id),
        status=ModelCacheStatus.NOT_INSTALLED,
        path=path,
        expected_bytes=spec.expected_bytes,
        actual_bytes=None,
        can_download=True,
        user_message=redact_text(user_message),
    )


def _model_path(*, cache_root: Path, spec: ModelDownloadSpec) -> Path:
    return Path(cache_root) / spec.model_id / spec.filename


def _validate_spec(spec: ModelDownloadSpec) -> None:
    if not spec.model_id.strip():
        raise ValueError("model_id must be a non-empty string")
    if Path(spec.model_id).is_absolute() or ".." in Path(spec.model_id).parts:
        raise ValueError("model_id must be a relative cache key")
    if not spec.filename.strip():
        raise ValueError("filename must be a non-empty string")
    filename_path = Path(spec.filename)
    if filename_path.is_absolute() or len(filename_path.parts) != 1:
        raise ValueError("filename must be a single relative filename")
    if spec.expected_bytes <= 0:
        raise ValueError("expected_bytes must be greater than zero")
    if spec.sha256 is not None and len(spec.sha256) != 64:
        raise ValueError("sha256 must be a 64-character hex digest")
    if spec.source_url is not None:
        parsed = urllib.parse.urlparse(spec.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use http or https")
        if parsed.username or parsed.password:
            raise ValueError("source_url must not include credentials")
    if (
        spec.manual_install_instructions is not None
        and not spec.manual_install_instructions.strip()
    ):
        raise ValueError("manual_install_instructions must be non-empty when provided")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
