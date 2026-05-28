from __future__ import annotations

import importlib
import importlib.util
import os
import tempfile
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from worktrace_agent.capture.ocr_worker import OcrCandidate, OcrEngine, OcrEngineResult
from worktrace_agent.privacy.redaction import redact_text


class OcrRuntimeStatus(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class OcrRuntimeConfig:
    enabled: bool = False
    provider: str = "paddleocr"
    module_name: str = "paddleocr"


@dataclass(frozen=True)
class OcrRuntimeAvailability:
    provider: str
    status: OcrRuntimeStatus
    can_run: bool
    user_message: str


class PaddleOcrRecognizer(Protocol):
    def predict(self, image_path: str) -> object:
        """Run OCR for the provided image path."""
        ...


@dataclass(frozen=True)
class OcrRuntimeBinding:
    availability: OcrRuntimeAvailability
    engine: OcrEngine | None


def check_ocr_runtime_availability(config: OcrRuntimeConfig) -> OcrRuntimeAvailability:
    _validate_config(config)
    provider = redact_text(config.provider.strip())
    if not config.enabled:
        return OcrRuntimeAvailability(
            provider=provider,
            status=OcrRuntimeStatus.DISABLED,
            can_run=False,
            user_message="OCR runtime is disabled. Recording continues without OCR.",
        )

    if importlib.util.find_spec(config.module_name) is None:
        return OcrRuntimeAvailability(
            provider=provider,
            status=OcrRuntimeStatus.UNAVAILABLE,
            can_run=False,
            user_message=(
                f"OCR runtime provider {provider} is not installed. "
                "Recording continues without OCR."
            ),
        )

    return OcrRuntimeAvailability(
        provider=provider,
        status=OcrRuntimeStatus.READY,
        can_run=True,
        user_message=f"OCR runtime provider {provider} is available for selective OCR.",
    )


class PaddleOcrEngine:
    def __init__(
        self,
        *,
        recognizer: PaddleOcrRecognizer,
        provider: str,
    ) -> None:
        self._recognizer = recognizer
        self.engine_name = redact_text(provider)

    def recognize(self, candidate: OcrCandidate) -> OcrEngineResult:
        if not candidate.image_bytes:
            raise RuntimeError("OCR runtime failed safely.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temporary_image:
            temporary_image.write(candidate.image_bytes)
            temp_path = temporary_image.name
        try:
            raw_result = self._recognizer.predict(temp_path)
            lines = _extract_text_lines(raw_result)
            confidence = sum(score for _text, score in lines) / len(lines)
            return OcrEngineResult(
                text="\n".join(text for text, _score in lines),
                confidence=confidence,
                metadata={"line_count": len(lines)},
            )
        except Exception as error:
            raise RuntimeError("OCR runtime failed safely.") from error
        finally:
            with suppress(OSError):
                os.unlink(temp_path)


def build_paddle_ocr_engine(
    config: OcrRuntimeConfig,
    *,
    recognizer_factory: Callable[[], PaddleOcrRecognizer] | None = None,
) -> OcrRuntimeBinding:
    availability = check_ocr_runtime_availability(config)
    if availability.status is not OcrRuntimeStatus.READY:
        return OcrRuntimeBinding(availability=availability, engine=None)

    provider = redact_text(config.provider.strip())
    try:
        recognizer = (
            recognizer_factory() if recognizer_factory is not None else _build_recognizer(config)
        )
    except Exception:
        return OcrRuntimeBinding(
            availability=OcrRuntimeAvailability(
                provider=provider,
                status=OcrRuntimeStatus.UNAVAILABLE,
                can_run=False,
                user_message=(
                    f"OCR runtime provider {provider} failed safely during initialization. "
                    "Recording continues without OCR."
                ),
            ),
            engine=None,
        )

    return OcrRuntimeBinding(
        availability=availability,
        engine=PaddleOcrEngine(recognizer=recognizer, provider=provider),
    )


def _build_recognizer(config: OcrRuntimeConfig) -> PaddleOcrRecognizer:
    module = importlib.import_module(config.module_name)
    paddle_ocr_class = getattr(module, "PaddleOCR", None)
    if not callable(paddle_ocr_class):
        raise RuntimeError("paddleocr runtime is missing PaddleOCR")
    return cast(
        PaddleOcrRecognizer,
        paddle_ocr_class(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        ),
    )


def _extract_text_lines(raw_result: object) -> list[tuple[str, float]]:
    if not isinstance(raw_result, list):
        raise ValueError("OCR runtime output must be a list")

    entries: list[object] = cast(list[object], raw_result)
    if len(entries) == 1 and isinstance(entries[0], list):
        entries = cast(list[object], entries[0])

    parsed_lines: list[tuple[str, float]] = []
    for entry in entries:
        parsed_lines.extend(_extract_text_lines_from_mapping(entry))
        if not isinstance(entry, (list, tuple)):
            continue
        old_style_entry = list(cast(Iterable[object], entry))
        if len(old_style_entry) < 2:
            continue
        text_block = old_style_entry[1]
        if not isinstance(text_block, (list, tuple)):
            continue
        old_style_text_block = list(cast(Iterable[object], text_block))
        if len(old_style_text_block) < 2:
            continue
        text = old_style_text_block[0]
        score = old_style_text_block[1]
        if not isinstance(text, str) or not text.strip():
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue

        clamped_score = max(0.0, min(1.0, float(score)))
        parsed_lines.append((text.strip(), clamped_score))

    if not parsed_lines:
        raise ValueError("OCR runtime produced no usable text lines")
    return parsed_lines


def _extract_text_lines_from_mapping(entry: object) -> list[tuple[str, float]]:
    if not isinstance(entry, dict):
        return []

    mapping = cast(dict[object, object], entry)
    payload = mapping.get("res")
    if isinstance(payload, dict):
        return _extract_rec_text_scores(cast(dict[object, object], payload))
    return _extract_rec_text_scores(mapping)


def _extract_rec_text_scores(payload: dict[object, object]) -> list[tuple[str, float]]:
    raw_texts = payload.get("rec_texts")
    raw_scores = payload.get("rec_scores")
    if raw_texts is None or raw_scores is None:
        return []

    texts = _as_list(raw_texts)
    scores = _as_list(raw_scores)
    parsed_lines: list[tuple[str, float]] = []
    for text, score in zip(texts, scores, strict=False):
        if not isinstance(text, str) or not text.strip():
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        parsed_lines.append((text.strip(), max(0.0, min(1.0, float(score)))))
    return parsed_lines


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return list(cast(list[object], value))
    if isinstance(value, tuple):
        return list(cast(tuple[object, ...], value))
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Iterable):
        return list(cast(Iterable[object], value))
    return [value]


def _validate_config(config: OcrRuntimeConfig) -> None:
    if not config.provider.strip():
        raise ValueError("provider must be a non-empty string")
    if not config.module_name.strip():
        raise ValueError("module_name must be a non-empty string")
