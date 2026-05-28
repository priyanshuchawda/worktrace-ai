from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

from worktrace_agent.capture.screenshot_sampler import (
    ScreenshotArtifactFormat,
    ScreenshotFrame,
    ScreenshotSampler,
    ScreenshotSamplerConfig,
    ScreenshotSkipReason,
    choose_screenshot_artifact_format,
)
from worktrace_agent.db.connection import initialize_database
from worktrace_agent.db.screenshots_repository import list_screenshots, save_screenshot
from worktrace_agent.db.session_state_repository import start_session

SESSION_ID = "sess_screenshot_001"
STARTED_AT = "2026-05-06T09:14:00+05:30"


def solid_frame(
    *,
    timestamp: str,
    width: int,
    height: int,
    value: int,
) -> ScreenshotFrame:
    return ScreenshotFrame(
        session_id=SESSION_ID,
        timestamp=timestamp,
        width=width,
        height=height,
        rgb_bytes=bytes([value, value, value]) * width * height,
    )


def checker_frame(
    *,
    timestamp: str,
    width: int,
    height: int,
    seed: int,
) -> ScreenshotFrame:
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            value = 255 if (x + y + seed) % 2 == 0 else 0
            pixels.extend([value, value, value])
    return ScreenshotFrame(
        session_id=SESSION_ID,
        timestamp=timestamp,
        width=width,
        height=height,
        rgb_bytes=bytes(pixels),
    )


def add_seconds(timestamp: str, seconds: int) -> str:
    return (datetime.fromisoformat(timestamp) + timedelta(seconds=seconds)).isoformat()


def test_sampler_defaults_accept_first_frame_and_skip_visual_duplicate() -> None:
    sampler = ScreenshotSampler()
    first = solid_frame(timestamp=STARTED_AT, width=16, height=9, value=64)
    duplicate = solid_frame(timestamp=add_seconds(STARTED_AT, 5), width=16, height=9, value=64)

    first_decision = sampler.process_frame(first)
    duplicate_decision = sampler.process_frame(duplicate)

    assert first_decision.accepted is not None
    assert first_decision.skipped is None
    assert duplicate_decision.accepted is None
    assert duplicate_decision.skipped is ScreenshotSkipReason.DUPLICATE
    assert sampler.config.interval_seconds == 5
    assert sampler.config.max_width == 1280


def test_screenshot_storage_policy_uses_lossless_png_and_defers_jpeg_webp() -> None:
    decision = choose_screenshot_artifact_format(width=1920, height=1080)

    assert decision.format is ScreenshotArtifactFormat.PNG
    assert decision.file_extension == ".png"
    assert decision.media_type == "image/png"
    assert decision.reason == "lossless_png_currently_supported_jpeg_webp_deferred"


def test_sampler_skips_frames_before_default_interval_and_scales_width_metadata() -> None:
    sampler = ScreenshotSampler()
    first = solid_frame(timestamp=STARTED_AT, width=2560, height=1440, value=90)
    too_soon = solid_frame(timestamp=add_seconds(STARTED_AT, 3), width=2560, height=1440, value=120)

    first_decision = sampler.process_frame(first)
    too_soon_decision = sampler.process_frame(too_soon)

    assert first_decision.accepted is not None
    assert first_decision.accepted.stored_width == 1280
    assert first_decision.accepted.stored_height == 720
    assert too_soon_decision.accepted is None
    assert too_soon_decision.skipped is ScreenshotSkipReason.INTERVAL


def test_sampler_enforces_hourly_storage_cap() -> None:
    sampler = ScreenshotSampler(
        ScreenshotSamplerConfig(max_hourly_bytes=400, duplicate_hamming_threshold=-1)
    )

    first = checker_frame(timestamp=STARTED_AT, width=8, height=8, seed=0)
    second = checker_frame(timestamp=add_seconds(STARTED_AT, 5), width=8, height=8, seed=1)
    third = checker_frame(timestamp=add_seconds(STARTED_AT, 10), width=8, height=8, seed=2)

    assert sampler.process_frame(first).accepted is not None
    assert sampler.process_frame(second).accepted is not None
    third_decision = sampler.process_frame(third)

    assert third_decision.accepted is None
    assert third_decision.skipped is ScreenshotSkipReason.STORAGE_CAP


def test_accepted_screenshot_metadata_round_trips_through_sqlite(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "worktrace.sqlite")
    try:
        start_session(connection, session_id=SESSION_ID, started_at=STARTED_AT)
        sampler = ScreenshotSampler()
        decision = sampler.process_frame(
            solid_frame(timestamp=STARTED_AT, width=16, height=9, value=80)
        )

        assert decision.accepted is not None
        save_screenshot(connection, decision.accepted)

        screenshots = list_screenshots(connection, SESSION_ID)

        assert screenshots == [decision.accepted]
        assert screenshots[0].source_event_id is None
        assert screenshots[0].storage_path.endswith(".png")
    finally:
        connection.close()


def test_ten_minute_simulated_sampling_cpu_average_stays_under_budget() -> None:
    sampler = ScreenshotSampler()
    started_at = datetime.fromisoformat(STARTED_AT)

    process_started = time.process_time()
    for index in range(120):
        sampler.process_frame(
            solid_frame(
                timestamp=(started_at + timedelta(seconds=index * 5)).isoformat(),
                width=8,
                height=8,
                value=42,
            )
        )
    process_seconds = time.process_time() - process_started

    simulated_cpu_average = process_seconds / (10 * 60) * 100
    assert simulated_cpu_average < sampler.config.max_cpu_average_percent
