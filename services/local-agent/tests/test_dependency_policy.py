from __future__ import annotations

import tomllib
from pathlib import Path

HEAVY_OPTIONAL_PACKAGES = {
    "accelerate",
    "huggingface-hub",
    "ollama",
    "pillow",
    "qwen-vl-utils",
    "safetensors",
    "sentence-transformers",
    "torch",
    "torchvision",
    "transformers",
}


def test_heavy_model_runtime_packages_are_opt_in() -> None:
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())

    required_dependencies = {
        _package_name(dependency) for dependency in pyproject["project"]["dependencies"]
    }
    optional_runtime_dependencies = {
        _package_name(dependency)
        for dependency in pyproject["project"]["optional-dependencies"]["local-model-runtimes"]
    }

    assert required_dependencies.isdisjoint(HEAVY_OPTIONAL_PACKAGES)
    assert HEAVY_OPTIONAL_PACKAGES.issubset(optional_runtime_dependencies)


def _package_name(requirement: str) -> str:
    return requirement.split("<", maxsplit=1)[0].split(">", maxsplit=1)[0].split("=", maxsplit=1)[0]
