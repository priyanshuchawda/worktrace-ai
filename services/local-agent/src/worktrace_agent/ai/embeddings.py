from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from worktrace_agent.capture.terminal_command_detector import redact_terminal_command
from worktrace_agent.timeline.deterministic import (
    require_confidence,
    require_evidence_event_ids,
    require_iso_datetime,
    require_non_empty,
)


@dataclass(frozen=True)
class CommandEmbeddingInput:
    event_id: str
    session_id: str
    timestamp: str
    command: str
    shell: str


class CommandEmbeddingModel(Protocol):
    @property
    def model_name(self) -> str:
        """Human-readable model name for safe metadata."""
        ...

    @property
    def model_version(self) -> str | None:
        """Optional model version for safe metadata."""
        ...

    def embed(self, text: str) -> tuple[float, ...]:
        """Return an embedding vector for command grouping."""
        ...


@dataclass(frozen=True)
class EmbeddedCommand:
    event_id: str
    session_id: str
    timestamp: str
    command: str
    command_hash: str
    shell: str
    embedding: tuple[float, ...]
    model_name: str
    model_version: str | None


@dataclass(frozen=True)
class CommandCluster:
    id: str
    session_id: str
    representative_command: str
    commands: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    average_similarity: float
    model_name: str
    model_version: str | None


def embed_command_inputs(
    commands: list[CommandEmbeddingInput],
    *,
    model: CommandEmbeddingModel,
) -> list[EmbeddedCommand]:
    return [embed_command_input(command, model=model) for command in commands]


def embed_command_input(
    command: CommandEmbeddingInput,
    *,
    model: CommandEmbeddingModel,
) -> EmbeddedCommand:
    _validate_command_input(command)
    redacted_command, _was_redacted = redact_terminal_command(command.command)
    embedding = _validate_embedding(model.embed(command.command))
    return EmbeddedCommand(
        event_id=command.event_id,
        session_id=command.session_id,
        timestamp=command.timestamp,
        command=redacted_command,
        command_hash=_hash_command(command.command),
        shell=command.shell,  # nosec B604
        embedding=embedding,
        model_name=require_non_empty(model.model_name, "model_name"),
        model_version=model.model_version,
    )


def cluster_similar_commands(
    commands: list[EmbeddedCommand],
    *,
    similarity_threshold: float = 0.9,
) -> list[CommandCluster]:
    require_confidence(similarity_threshold)
    clusters: list[list[EmbeddedCommand]] = []

    for command in commands:
        for cluster in clusters:
            if _similar_enough(command, cluster, threshold=similarity_threshold):
                cluster.append(command)
                break
        else:
            clusters.append([command])

    return [
        _build_cluster(index=index, commands=cluster)
        for index, cluster in enumerate(clusters)
        if len(cluster) > 1
    ]


def cosine_similarity(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    if len(first) != len(second):
        raise ValueError("embedding vectors must have the same dimensions")
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        raise ValueError("embedding vectors must not be zero vectors")
    return sum(a * b for a, b in zip(first, second, strict=True)) / (first_norm * second_norm)


def _validate_command_input(command: CommandEmbeddingInput) -> None:
    require_non_empty(command.event_id, "event_id")
    require_non_empty(command.session_id, "session_id")
    require_iso_datetime(command.timestamp, "timestamp")
    require_non_empty(command.command, "command")
    require_non_empty(command.shell, "shell")


def _validate_embedding(embedding: tuple[float, ...]) -> tuple[float, ...]:
    if not embedding:
        raise ValueError("embedding must contain at least one dimension")
    if not all(math.isfinite(value) for value in embedding):
        raise ValueError("embedding values must be finite")
    if not any(value != 0 for value in embedding):
        raise ValueError("embedding must not be a zero vector")
    return tuple(float(value) for value in embedding)


def _similar_enough(
    command: EmbeddedCommand,
    cluster: list[EmbeddedCommand],
    *,
    threshold: float,
) -> bool:
    return (
        max(cosine_similarity(command.embedding, member.embedding) for member in cluster)
        >= threshold
    )


def _build_cluster(*, index: int, commands: list[EmbeddedCommand]) -> CommandCluster:
    if not commands:
        raise ValueError("command cluster requires at least one command")
    first_command = commands[0]
    evidence_event_ids = require_evidence_event_ids(tuple(command.event_id for command in commands))
    similarities = [
        cosine_similarity(first.embedding, second.embedding)
        for first_index, first in enumerate(commands)
        for second in commands[first_index + 1 :]
    ]
    average_similarity = sum(similarities) / len(similarities)
    return CommandCluster(
        id=f"{first_command.session_id}-command-cluster-{index:03d}",
        session_id=first_command.session_id,
        representative_command=first_command.command,
        commands=tuple(command.command for command in commands),
        evidence_event_ids=evidence_event_ids,
        average_similarity=require_confidence(average_similarity),
        model_name=first_command.model_name,
        model_version=first_command.model_version,
    )


def _hash_command(command: str) -> str:
    return f"sha256:{hashlib.sha256(command.encode('utf-8')).hexdigest()}"
