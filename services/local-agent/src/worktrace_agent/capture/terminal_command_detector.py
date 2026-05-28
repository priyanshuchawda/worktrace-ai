from __future__ import annotations

import hashlib
import re
from typing import Final

from worktrace_agent.domain.raw_event import RawEvent, build_raw_event
from worktrace_agent.privacy.redaction import REDACTION_TOKEN, redact_text

SECRET_ASSIGNMENT_PATTERN: Final = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PASS|KEY)[A-Z0-9_]*=)([^\s;&|]+)"
)
SECRET_FLAG_PATTERN: Final = re.compile(
    r"(?i)(--(?:api-key|token|secret|password|pass|key)(?:=|\s+))([^\s;&|]+)"
)
BEARER_PATTERN: Final = re.compile(r"(?i)(authorization:\s*bearer\s+)([^\s\"']+)")
URL_CREDENTIAL_PATTERN: Final = re.compile(r"://([^:@/\s]+):?([^@/\s]*)@")


def normalize_terminal_command(
    *,
    session_id: str,
    timestamp: str,
    command: str,
    shell: str,
    exit_code: int | None = None,
) -> RawEvent:
    redacted_command, was_redacted = redact_terminal_command(command)
    command_hash = hash_command(redacted_command)

    return build_raw_event(
        event_id=build_terminal_event_id(
            session_id=session_id,
            timestamp=timestamp,
            command_hash=command_hash,
        ),
        session_id=session_id,
        timestamp=timestamp,
        source="terminal_command_detector",
        event_type="terminal_command",
        privacy_level="redacted" if was_redacted else "safe",
        confidence=1,
        metadata={
            "command": redacted_command,
            "shell": require_non_empty(shell, "shell"),
            "exit_code": exit_code,
            "redacted": was_redacted,
            "command_hash": command_hash,
        },
    )


def redact_terminal_command(command: str) -> tuple[str, bool]:
    require_non_empty(command, "command")
    redacted = redact_text(command)
    redacted = SECRET_ASSIGNMENT_PATTERN.sub(rf"\1{REDACTION_TOKEN}", redacted)
    redacted = SECRET_FLAG_PATTERN.sub(rf"\1{REDACTION_TOKEN}", redacted)
    redacted = BEARER_PATTERN.sub(rf"\1{REDACTION_TOKEN}", redacted)
    redacted = URL_CREDENTIAL_PATTERN.sub(f"://{REDACTION_TOKEN}@", redacted)
    return redacted, redacted != command


def hash_command(command: str) -> str:
    require_non_empty(command, "command")
    return hashlib.sha256(command.encode()).hexdigest()


def build_terminal_event_id(*, session_id: str, timestamp: str, command_hash: str) -> str:
    digest = hashlib.sha256(f"{session_id}|{timestamp}|{command_hash}".encode()).hexdigest()
    return f"{session_id}-terminal-{digest[:16]}"


def require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value
