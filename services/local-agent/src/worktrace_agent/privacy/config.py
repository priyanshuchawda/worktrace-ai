from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from worktrace_agent.privacy.redaction import count_privacy_leaks

MAX_POLICY_ENTRIES = 64
MAX_POLICY_ENTRY_CHARS = 120


class PrivacyPolicyConfigError(ValueError):
    pass


@dataclass(frozen=True)
class PrivacyPolicyConfig:
    allowlist: tuple[str, ...] = ()
    blocklist: tuple[str, ...] = ()
    clipboard_safe_mode: bool = True


class PrivacyPolicyConfigService:
    def __init__(self, *, config_path: Path) -> None:
        self._config_path = Path(config_path)

    def load(self) -> PrivacyPolicyConfig:
        if not self._config_path.exists():
            return PrivacyPolicyConfig()
        try:
            raw_object: object = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PrivacyPolicyConfigError("Privacy policy config could not be read.") from error
        if not isinstance(raw_object, dict):
            raise PrivacyPolicyConfigError("Privacy policy config must be an object.")
        return parse_privacy_policy_config(cast(dict[str, Any], raw_object))

    def save(self, config: PrivacyPolicyConfig) -> PrivacyPolicyConfig:
        normalized = parse_privacy_policy_config(
            {
                "allowlist": list(config.allowlist),
                "blocklist": list(config.blocklist),
                "clipboard_safe_mode": config.clipboard_safe_mode,
            }
        )
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(
                {
                    "allowlist": list(normalized.allowlist),
                    "blocklist": list(normalized.blocklist),
                    "clipboard_safe_mode": normalized.clipboard_safe_mode,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return normalized


def parse_privacy_policy_config(raw: dict[str, Any]) -> PrivacyPolicyConfig:
    return PrivacyPolicyConfig(
        allowlist=_normalize_entries(raw.get("allowlist", []), "allowlist"),
        blocklist=_normalize_entries(raw.get("blocklist", []), "blocklist"),
        clipboard_safe_mode=_require_bool(
            raw.get("clipboard_safe_mode", True), "clipboard_safe_mode"
        ),
    )


def _normalize_entries(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PrivacyPolicyConfigError(f"{field_name} must be a list.")
    entries: list[str] = []
    seen: set[str] = set()
    for item in cast(list[object], value):
        if not isinstance(item, str):
            raise PrivacyPolicyConfigError(f"{field_name} entries must be strings.")
        entry = item.strip()
        if not entry:
            continue
        if len(entry) > MAX_POLICY_ENTRY_CHARS:
            raise PrivacyPolicyConfigError(f"{field_name} entry is too long.")
        if count_privacy_leaks(entry) > 0:
            raise PrivacyPolicyConfigError(f"{field_name} entry contains sensitive text.")
        key = entry.casefold()
        if key in seen:
            continue
        entries.append(entry)
        seen.add(key)
        if len(entries) > MAX_POLICY_ENTRIES:
            raise PrivacyPolicyConfigError(f"{field_name} has too many entries.")
    return tuple(entries)


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise PrivacyPolicyConfigError(f"{field_name} must be a boolean.")
    return value
