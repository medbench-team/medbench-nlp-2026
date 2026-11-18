"""LLM run configuration (configs/llm_ceiling.yaml) and the API key (never logged)."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from medbench.data import TaskName

DEFAULT_CONFIG = Path("configs/llm_ceiling.yaml")
ENV_FILE = Path(".env")
KEY_NAME = "OLLAMA_API_KEY"


class MissingApiKeyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(f"Нет ключа {KEY_NAME}: задайте его в окружении или в файле .env (значение не выводится).")


class Generation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature: float = 0.0
    reasoning: bool = True
    num_predict: int = Field(8192, gt=0)


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str = "https://ollama.com"
    models: tuple[str, ...]
    prompt_version: str = "v1"
    generation: Generation = Generation()
    concurrency: int = Field(4, ge=1, le=16)
    format_retries: int = Field(2, ge=0, le=5)
    http_retries: int = Field(5, ge=0, le=10)
    timeout_s: float = Field(300, gt=0)
    fallback: dict[TaskName, str | int]
    cache_path: Path = Path("data/llm_cache/cache.sqlite")


def load_llm_config(path: Path | str = DEFAULT_CONFIG) -> LLMConfig:
    return LLMConfig.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def run_params(config: LLMConfig) -> dict[str, Any]:
    """Parameters that define a run configuration (→ config_hash, spec 002)."""
    return {
        "prompt_version": config.prompt_version,
        "generation": config.generation.model_dump(),
        "format_retries": config.format_retries,
        "fallback": {str(k): v for k, v in config.fallback.items()},
    }


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def api_key(env_file: Path = ENV_FILE) -> str:
    key = os.environ.get(KEY_NAME) or _read_env_file(env_file).get(KEY_NAME)
    if not key:
        raise MissingApiKeyError()
    return key
