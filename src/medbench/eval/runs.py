"""Run registry: results/runs/<run_id>/{preds.jsonl, meta.json} (FR-005, FR-006, ADR-017)."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from medbench.data import DataConfig, Role, TaskName, default_config
from medbench.eval.errors import EvalError, FinalRunExistsError, StaleRunError
from medbench.eval.metrics import TaskMetrics
from medbench.eval.predictions import Prediction, read_predictions, validate_predictions, write_predictions
from medbench.eval.scoring import score

RESULTS_DIR = Path("results")
SAVABLE_ROLES = (Role.TUNE, Role.FINAL, Role.SUBMIT)


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    approach: str = Field(pattern=r"^[a-z0-9-]+$")
    model: str
    params: dict[str, Any] = Field(default_factory=dict)
    config_hash: str
    task: TaskName
    role: Role
    n_examples: int
    metrics: dict[str, float] | None = None
    invalid_rate: float | None = None
    usage: dict[str, float] | None = None
    code_commit: str
    data_commit: str
    created_at: str
    justification: str | None = None
    notes: str | None = None


class Run(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    meta: RunMeta
    predictions: list[Prediction]


def config_hash(approach: str, model: str, params: dict[str, Any] | None = None) -> str:
    """sha256 of canonical JSON of {approach, model, params}; independent of task, role and data."""
    payload = json.dumps({"approach": approach, "model": model, "params": params or {}},
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def code_commit() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{head}-dirty" if dirty else head


def runs_dir(results_dir: Path | str = RESULTS_DIR) -> Path:
    return Path(results_dir) / "runs"


def _read_meta(run_path: Path) -> RunMeta:
    return RunMeta.model_validate_json((run_path / "meta.json").read_text(encoding="utf-8"))


def list_runs(results_dir: Path | str = RESULTS_DIR) -> list[RunMeta]:
    base = runs_dir(results_dir)
    if not base.is_dir():
        return []
    return sorted((_read_meta(p) for p in base.iterdir() if (p / "meta.json").is_file()), key=lambda m: m.run_id)


def save_run(
    task: TaskName | str,
    role: Role | str,
    predictions: list[Prediction],
    *,
    approach: str,
    model: str,
    params: dict[str, Any] | None = None,
    usage: dict[str, float] | None = None,
    justification: str | None = None,
    notes: str | None = None,
    config: DataConfig | None = None,
    results_dir: Path | str = RESULTS_DIR,
) -> Run:
    """Validate, score (except submit) and store a run. The only way approaches record results."""
    task, role, config = TaskName(task), Role(role), config or default_config()
    if role not in SAVABLE_ROLES:
        raise EvalError(f"Роль {role} не сохраняется: допустимы tune, final, submit.")
    chash = config_hash(approach, model, params)
    if role is Role.FINAL:
        previous = [m for m in list_runs(results_dir) if m.role is Role.FINAL and m.task == task and m.config_hash == chash]
        if previous and not (justification and justification.strip()):
            raise FinalRunExistsError(
                f"{task}: финальный прогон этой конфигурации уже есть ({previous[-1].run_id}). "
                "Один final на конфигурацию (конституция, принцип I); повтор — только с --justification."
            )
    validate_predictions(task, role, predictions, config)
    metrics: TaskMetrics | None = None if role is Role.SUBMIT else score(task, predictions, role, config)
    created = datetime.now(UTC)
    run_id = f"{created:%Y%m%d-%H%M%S}_{approach}_{task}_{role}_{chash[:8]}"
    meta = RunMeta(
        run_id=run_id, approach=approach, model=model, params=params or {}, config_hash=chash, task=task, role=role,
        n_examples=len(predictions), metrics=metrics.as_dict() if metrics else None,
        invalid_rate=sum(p.invalid for p in predictions) / len(predictions) if predictions else None,
        usage=usage, code_commit=code_commit(), data_commit=config.source.commit,
        created_at=created.isoformat(timespec="seconds"), justification=justification, notes=notes,
    )
    path, n = runs_dir(results_dir) / run_id, 1
    while path.exists():  # same config saved twice within one second
        n += 1
        path = runs_dir(results_dir) / f"{run_id}-{n}"
    meta.run_id = path.name
    write_predictions(path / "preds.jsonl", predictions)
    (path / "meta.json").write_text(meta.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return Run(path=path, meta=meta, predictions=predictions)


def load_run(run_path: Path | str, config: DataConfig | None = None) -> Run:
    run_path, config = Path(run_path), config or default_config()
    meta = _read_meta(run_path)
    if meta.data_commit != config.source.commit:
        raise StaleRunError(
            f"{meta.run_id}: получен на данных {meta.data_commit[:7]}, текущие — {config.source.commit[:7]}."
        )
    return Run(path=run_path, meta=meta, predictions=read_predictions(run_path / "preds.jsonl"))


def rescore(run_path: Path | str, config: DataConfig | None = None) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    """Recompute metrics of a saved run; returns (stored, recomputed)."""
    run = load_run(run_path, config)
    if run.meta.role is Role.SUBMIT:
        return run.meta.metrics, None
    return run.meta.metrics, score(run.meta.task, run.predictions, run.meta.role, config).as_dict()
