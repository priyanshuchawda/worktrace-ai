from __future__ import annotations

import os
import re
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

import uvicorn

DEFAULT_SIDECAR_HOST = "127.0.0.1"
DEFAULT_SIDECAR_PORT = 8765
LOCAL_ONLY_HOSTS = {"127.0.0.1", "localhost"}
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class SidecarServerConfig:
    host: str
    port: int


def read_sidecar_server_config() -> SidecarServerConfig:
    host = os.environ.get("WORKTRACE_SIDECAR_HOST", DEFAULT_SIDECAR_HOST)
    if host not in LOCAL_ONLY_HOSTS:
        raise SystemExit("WORKTRACE_SIDECAR_HOST must be 127.0.0.1 or localhost")

    port_text = os.environ.get("WORKTRACE_SIDECAR_PORT", str(DEFAULT_SIDECAR_PORT))
    try:
        port = int(port_text)
    except ValueError as error:
        raise SystemExit("WORKTRACE_SIDECAR_PORT must be an integer") from error
    if port < 1 or port > 65535:
        raise SystemExit("WORKTRACE_SIDECAR_PORT must be between 1 and 65535")

    return SidecarServerConfig(host=host, port=port)


def load_local_env_file(
    *,
    start_dir: Path | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> Path | None:
    selected_start_dir = (start_dir or Path.cwd()).resolve()
    selected_environ = environ if environ is not None else os.environ
    env_path = _find_local_env_file(selected_start_dir)
    if env_path is None:
        return None

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if key not in selected_environ:
            selected_environ[key] = value
    return env_path


def _find_local_env_file(start_dir: Path) -> Path | None:
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            return None
    return None


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].lstrip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    if not ENV_KEY_PATTERN.fullmatch(key):
        return None
    return key, _unquote_env_value(value.strip())


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def main() -> None:
    load_local_env_file()
    config = read_sidecar_server_config()
    uvicorn.run(
        "worktrace_agent.api.app:app",
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
