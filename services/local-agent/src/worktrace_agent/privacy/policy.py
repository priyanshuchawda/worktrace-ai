from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ClipboardStorageMode = Literal["metadata_only", "disabled"]


@dataclass(frozen=True)
class PrivacyPolicy:
    allowlist: tuple[str, ...] = ()
    blocklist: tuple[str, ...] = ()
    private_mode: bool = False
    clipboard_safe_mode: bool = True

    @property
    def clipboard_storage_mode(self) -> ClipboardStorageMode:
        if self.private_mode:
            return "disabled"
        return "metadata_only"

    def should_capture_app(self, app_name: str) -> bool:
        normalized_app = normalize_name(app_name)
        if self.private_mode:
            return False
        blocklisted_apps = {normalize_name(app) for app in self.blocklist}
        allowed_apps = {normalize_name(app) for app in self.allowlist}
        if normalized_app in blocklisted_apps:
            return False
        return not self.allowlist or normalized_app in allowed_apps

    def should_capture_app_identity(self, *, app_name: str, process_name: str) -> bool:
        if self.private_mode:
            return False

        normalized_names = {normalize_name(app_name), normalize_name(process_name)}
        blocklisted_apps = {normalize_name(app) for app in self.blocklist}
        if normalized_names & blocklisted_apps:
            return False

        allowed_apps = {normalize_name(app) for app in self.allowlist}
        return not allowed_apps or bool(normalized_names & allowed_apps)

    def should_capture_source(self, source: str) -> bool:
        if self.private_mode:
            return False
        return bool(source.strip())

    def should_capture_clipboard_content(self) -> bool:
        return False if self.private_mode or self.clipboard_safe_mode else False


def normalize_name(value: str) -> str:
    return value.strip().casefold()
