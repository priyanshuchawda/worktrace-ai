from __future__ import annotations

import asyncio
import ctypes
import os
import sqlite3
import struct
import zlib
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from worktrace_agent.capture.screenshot_sampler import (
    ScreenshotArtifact,
    ScreenshotFrame,
    ScreenshotSampler,
)
from worktrace_agent.db.raw_events_repository import list_raw_events
from worktrace_agent.db.screenshots_repository import (
    DEFAULT_SCREENSHOT_RETENTION_CONFIG,
    ScreenshotRetentionConfig,
    prune_screenshots_for_session,
    save_screenshot,
)
from worktrace_agent.privacy.policy import PrivacyPolicy

SCREENSHOT_SOURCE = "screenshot_sampler"
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


class ScreenshotProvider(Protocol):
    def capture_frame(self, *, session_id: str, timestamp: str) -> ScreenshotFrame | None:
        pass


class WindowsScreenshotProvider:
    def capture_frame(self, *, session_id: str, timestamp: str) -> ScreenshotFrame | None:
        if os.name != "nt":
            return None

        user32 = cast(Any, ctypes.WinDLL("user32", use_last_error=True))
        gdi32 = cast(Any, ctypes.WinDLL("gdi32", use_last_error=True))

        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        if width <= 0 or height <= 0:
            return None

        screen_dc = user32.GetDC(0)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        previous_object = gdi32.SelectObject(memory_dc, bitmap)
        try:
            if not gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, 0, 0, SRCCOPY):
                return None
            rgb_bytes = _read_bitmap_rgb(gdi32, memory_dc, bitmap, width, height)
        finally:
            gdi32.SelectObject(memory_dc, previous_object)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(0, screen_dc)

        return ScreenshotFrame(
            session_id=session_id,
            timestamp=timestamp,
            width=width,
            height=height,
            rgb_bytes=rgb_bytes,
        )


class ScreenshotCaptureWorker:
    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        session_id: str,
        artifact_root: Path,
        provider: ScreenshotProvider,
        sampler: ScreenshotSampler | None = None,
        privacy_policy: PrivacyPolicy | None = None,
        retention_config: ScreenshotRetentionConfig | None = None,
        interval_seconds: float = 5,
    ) -> None:
        self._connection = connection
        self._session_id = session_id
        self._artifact_root = Path(artifact_root)
        self._provider = provider
        self._sampler = sampler or ScreenshotSampler()
        self._privacy_policy = privacy_policy or PrivacyPolicy()
        self._retention_config = retention_config or DEFAULT_SCREENSHOT_RETENTION_CONFIG
        self._interval_seconds = interval_seconds
        self._stop_event = asyncio.Event()
        self.poll_count = 0
        self.last_error: str | None = None

    def poll_once(
        self,
        *,
        timestamp: str | None = None,
        active_process_name: str | None = None,
    ) -> ScreenshotArtifact | None:
        if not self._privacy_policy.should_capture_source(SCREENSHOT_SOURCE):
            return None
        if active_process_name and not self._privacy_policy.should_capture_app(active_process_name):
            return None

        capture_timestamp = timestamp or datetime.now(UTC).astimezone().isoformat()
        try:
            frame = self._provider.capture_frame(
                session_id=self._session_id,
                timestamp=capture_timestamp,
            )
        except Exception:
            self.last_error = "screenshot_provider_error"
            return None

        self.poll_count += 1
        if frame is None:
            return None

        source_event_id = self._nearest_active_window_event_id(capture_timestamp)
        decision = self._sampler.process_frame(frame, source_event_id=source_event_id)
        if decision.accepted is None:
            return None

        stored_rgb = downscale_rgb_nearest(
            rgb_bytes=frame.rgb_bytes,
            width=frame.width,
            height=frame.height,
            stored_width=decision.accepted.stored_width,
            stored_height=decision.accepted.stored_height,
        )
        artifact_bytes = encode_png_rgb(
            rgb_bytes=stored_rgb,
            width=decision.accepted.stored_width,
            height=decision.accepted.stored_height,
        )
        artifact = replace(decision.accepted, byte_size=len(artifact_bytes))
        try:
            self._write_artifact_bytes(artifact=artifact, artifact_bytes=artifact_bytes)
            save_screenshot(self._connection, artifact)
            prune_screenshots_for_session(
                self._connection,
                session_id=self._session_id,
                artifact_root=self._artifact_root,
                config=self._retention_config,
            )
        except OSError:
            self.last_error = "screenshot_storage_error"
            return None
        except ValueError:
            self.last_error = "screenshot_storage_error"
            return None
        self.last_error = None
        return artifact

    async def run(
        self,
        *,
        active_process_name: str | None = None,
        active_process_name_provider: Callable[[], str | None] | None = None,
    ) -> None:
        while not self._stop_event.is_set():
            current_process_name = (
                active_process_name_provider()
                if active_process_name_provider
                else active_process_name
            )
            self.poll_once(active_process_name=current_process_name)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except TimeoutError:
                continue

    async def stop(self) -> None:
        self._stop_event.set()
        await asyncio.sleep(0)

    def _nearest_active_window_event_id(self, timestamp: str) -> str | None:
        target = datetime.fromisoformat(timestamp)
        candidates = [
            event
            for event in list_raw_events(self._connection, self._session_id)
            if event.source == "active_window" and event.type == "active_window_changed"
        ]
        if not candidates:
            return None

        nearest = min(
            candidates,
            key=lambda event: abs(datetime.fromisoformat(event.timestamp) - target),
        )
        return nearest.id

    def _write_artifact_bytes(
        self,
        *,
        artifact: ScreenshotArtifact,
        artifact_bytes: bytes,
    ) -> None:
        resolved_root = self._artifact_root.resolve()
        target = (resolved_root / artifact.storage_path).resolve()
        try:
            target.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError("screenshot artifact path is outside artifact root") from error

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = target.with_suffix(f"{target.suffix}.tmp")
        temporary_path.write_bytes(artifact_bytes)
        temporary_path.replace(target)


def downscale_rgb_nearest(
    *,
    rgb_bytes: bytes,
    width: int,
    height: int,
    stored_width: int,
    stored_height: int,
) -> bytes:
    if width == stored_width and height == stored_height:
        return rgb_bytes

    output = bytearray(stored_width * stored_height * 3)
    for stored_y in range(stored_height):
        source_y = min(height - 1, int(stored_y * height / stored_height))
        for stored_x in range(stored_width):
            source_x = min(width - 1, int(stored_x * width / stored_width))
            source_index = (source_y * width + source_x) * 3
            target_index = (stored_y * stored_width + stored_x) * 3
            output[target_index : target_index + 3] = rgb_bytes[source_index : source_index + 3]
    return bytes(output)


def encode_png_rgb(*, rgb_bytes: bytes, width: int, height: int) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError("png dimensions must be positive")
    expected_bytes = width * height * 3
    if len(rgb_bytes) != expected_bytes:
        raise ValueError("rgb_bytes must contain exactly width * height * 3 bytes")

    rows = bytearray()
    row_stride = width * 3
    for y in range(height):
        row_start = y * row_stride
        rows.append(0)
        rows.extend(rgb_bytes[row_start : row_start + row_stride])

    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
            ),
            _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=6)),
            _png_chunk(b"IEND", b""),
        )
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return (
        struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum & 0xFFFFFFFF)
    )


class BitmapInfoHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class BitmapInfo(ctypes.Structure):
    _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", ctypes.c_uint32 * 3)]


def _read_bitmap_rgb(gdi32: Any, memory_dc: int, bitmap: int, width: int, height: int) -> bytes:
    bitmap_info = BitmapInfo()
    bitmap_info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
    bitmap_info.bmiHeader.biWidth = width
    bitmap_info.bmiHeader.biHeight = -height
    bitmap_info.bmiHeader.biPlanes = 1
    bitmap_info.bmiHeader.biBitCount = 32
    bitmap_info.bmiHeader.biCompression = BI_RGB
    raw_size = width * height * 4
    raw_buffer = (ctypes.c_ubyte * raw_size)()

    rows = gdi32.GetDIBits(
        memory_dc,
        bitmap,
        0,
        height,
        raw_buffer,
        ctypes.byref(bitmap_info),
        DIB_RGB_COLORS,
    )
    if rows == 0:
        raise RuntimeError("screenshot_capture_failed")

    rgb = bytearray(width * height * 3)
    for pixel_index in range(width * height):
        source_index = pixel_index * 4
        target_index = pixel_index * 3
        blue = raw_buffer[source_index]
        green = raw_buffer[source_index + 1]
        red = raw_buffer[source_index + 2]
        rgb[target_index : target_index + 3] = bytes((red, green, blue))
    return bytes(rgb)
