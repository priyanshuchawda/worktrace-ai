from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

DEFAULT_INTERVAL_SECONDS: Final = 5
DEFAULT_MAX_WIDTH: Final = 1280
DEFAULT_MAX_HOURLY_BYTES: Final = 250 * 1024 * 1024
DEFAULT_DUPLICATE_HAMMING_THRESHOLD: Final = 3
DEFAULT_MAX_CPU_AVERAGE_PERCENT: Final = 15.0
VISUAL_HASH_GRID_SIZE: Final = 8


class ScreenshotSkipReason(StrEnum):
    INTERVAL = "interval"
    DUPLICATE = "duplicate"
    STORAGE_CAP = "storage_cap"


class ScreenshotArtifactFormat(StrEnum):
    PNG = "png"


@dataclass(frozen=True)
class ScreenshotArtifactFormatDecision:
    format: ScreenshotArtifactFormat
    file_extension: str
    media_type: str
    reason: str


@dataclass(frozen=True)
class ScreenshotSamplerConfig:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    max_width: int = DEFAULT_MAX_WIDTH
    max_hourly_bytes: int = DEFAULT_MAX_HOURLY_BYTES
    duplicate_hamming_threshold: int = DEFAULT_DUPLICATE_HAMMING_THRESHOLD
    max_cpu_average_percent: float = DEFAULT_MAX_CPU_AVERAGE_PERCENT


@dataclass(frozen=True)
class ScreenshotFrame:
    session_id: str
    timestamp: str
    width: int
    height: int
    rgb_bytes: bytes


@dataclass(frozen=True)
class ScreenshotArtifact:
    id: str
    session_id: str
    source_event_id: str | None
    timestamp: str
    width: int
    height: int
    stored_width: int
    stored_height: int
    byte_size: int
    content_hash: str
    visual_hash: str
    storage_path: str


@dataclass(frozen=True)
class ScreenshotDecision:
    accepted: ScreenshotArtifact | None
    skipped: ScreenshotSkipReason | None


class ScreenshotSampler:
    def __init__(self, config: ScreenshotSamplerConfig | None = None) -> None:
        self.config = config or ScreenshotSamplerConfig()
        self._last_sample_at: dict[str, datetime] = {}
        self._last_visual_hash: dict[str, str] = {}
        self._hourly_bytes: dict[tuple[str, str], int] = {}
        self._accepted_counts: dict[str, int] = {}

    def process_frame(
        self,
        frame: ScreenshotFrame,
        *,
        source_event_id: str | None = None,
    ) -> ScreenshotDecision:
        validate_frame(frame)
        timestamp = parse_offset_datetime(frame.timestamp)

        last_sample_at = self._last_sample_at.get(frame.session_id)
        if (
            last_sample_at is not None
            and (timestamp - last_sample_at).total_seconds() < self.config.interval_seconds
        ):
            return ScreenshotDecision(accepted=None, skipped=ScreenshotSkipReason.INTERVAL)

        self._last_sample_at[frame.session_id] = timestamp
        visual_hash = build_visual_hash(frame)
        previous_hash = self._last_visual_hash.get(frame.session_id)
        if (
            previous_hash is not None
            and hamming_distance(previous_hash, visual_hash)
            <= self.config.duplicate_hamming_threshold
        ):
            return ScreenshotDecision(accepted=None, skipped=ScreenshotSkipReason.DUPLICATE)

        byte_size = len(frame.rgb_bytes)
        hourly_key = (
            frame.session_id,
            timestamp.replace(minute=0, second=0, microsecond=0).isoformat(),
        )
        current_hour_bytes = self._hourly_bytes.get(hourly_key, 0)
        if current_hour_bytes + byte_size > self.config.max_hourly_bytes:
            return ScreenshotDecision(accepted=None, skipped=ScreenshotSkipReason.STORAGE_CAP)

        artifact = self._build_artifact(
            frame=frame,
            source_event_id=source_event_id,
            byte_size=byte_size,
            visual_hash=visual_hash,
        )
        self._last_visual_hash[frame.session_id] = visual_hash
        self._hourly_bytes[hourly_key] = current_hour_bytes + byte_size
        self._accepted_counts[frame.session_id] = self._accepted_counts.get(frame.session_id, 0) + 1

        return ScreenshotDecision(accepted=artifact, skipped=None)

    def _build_artifact(
        self,
        *,
        frame: ScreenshotFrame,
        source_event_id: str | None,
        byte_size: int,
        visual_hash: str,
    ) -> ScreenshotArtifact:
        stored_width, stored_height = calculate_stored_dimensions(
            width=frame.width,
            height=frame.height,
            max_width=self.config.max_width,
        )
        format_decision = choose_screenshot_artifact_format(
            width=stored_width,
            height=stored_height,
        )
        screenshot_index = self._accepted_counts.get(frame.session_id, 0)
        screenshot_id = f"{frame.session_id}-screenshot-{screenshot_index:03d}"
        return ScreenshotArtifact(
            id=screenshot_id,
            session_id=frame.session_id,
            source_event_id=source_event_id,
            timestamp=frame.timestamp,
            width=frame.width,
            height=frame.height,
            stored_width=stored_width,
            stored_height=stored_height,
            byte_size=byte_size,
            content_hash=hashlib.sha256(frame.rgb_bytes).hexdigest(),
            visual_hash=visual_hash,
            storage_path=f"screenshots/{screenshot_id}{format_decision.file_extension}",
        )


def choose_screenshot_artifact_format(
    *, width: int, height: int
) -> ScreenshotArtifactFormatDecision:
    if width <= 0 or height <= 0:
        raise ValueError("screenshot dimensions must be positive")
    return ScreenshotArtifactFormatDecision(
        format=ScreenshotArtifactFormat.PNG,
        file_extension=".png",
        media_type="image/png",
        reason="lossless_png_currently_supported_jpeg_webp_deferred",
    )


def validate_frame(frame: ScreenshotFrame) -> None:
    if not frame.session_id.strip():
        raise ValueError("session_id must be a non-empty string")
    parse_offset_datetime(frame.timestamp)
    if frame.width <= 0 or frame.height <= 0:
        raise ValueError("screenshot frame dimensions must be positive")
    expected_bytes = frame.width * frame.height * 3
    if len(frame.rgb_bytes) != expected_bytes:
        raise ValueError("rgb_bytes must contain exactly width * height * 3 bytes")


def parse_offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")
    return parsed


def calculate_stored_dimensions(*, width: int, height: int, max_width: int) -> tuple[int, int]:
    if width <= max_width:
        return width, height

    scale = max_width / width
    stored_height = max(1, round(height * scale))
    return max_width, stored_height


def build_visual_hash(frame: ScreenshotFrame) -> str:
    luminance_values: list[int] = []
    for grid_y in range(VISUAL_HASH_GRID_SIZE):
        y = min(frame.height - 1, int((grid_y + 0.5) * frame.height / VISUAL_HASH_GRID_SIZE))
        for grid_x in range(VISUAL_HASH_GRID_SIZE):
            x = min(frame.width - 1, int((grid_x + 0.5) * frame.width / VISUAL_HASH_GRID_SIZE))
            byte_index = (y * frame.width + x) * 3
            red = frame.rgb_bytes[byte_index]
            green = frame.rgb_bytes[byte_index + 1]
            blue = frame.rgb_bytes[byte_index + 2]
            luminance_values.append((red + green + blue) // 3)

    average_luminance = sum(luminance_values) / len(luminance_values)
    hash_value = 0
    for luminance in luminance_values:
        hash_value = (hash_value << 1) | int(luminance >= average_luminance)

    return f"{hash_value:016x}"


def hamming_distance(first_hash: str, second_hash: str) -> int:
    return (int(first_hash, 16) ^ int(second_hash, 16)).bit_count()
