"""Prediction rows (`preds.jsonl`) and their validation against a split role (data-model.md)."""

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from medbench.data import DataConfig, NERExample, Role, TaskName, get_role
from medbench.data.schemas import NER_TAGS
from medbench.eval.errors import PredictionError

RAW_MAX = 500
LABELS: dict[TaskName, frozenset] = {
    TaskName.NLI: frozenset({"entailment", "contradiction", "neutral"}),
    TaskName.DANET: frozenset({"да", "нет"}),
    TaskName.TEST: frozenset({1, 2, 3, 4}),
}


class Prediction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    prediction: str | int | list[str]
    invalid: bool = False
    raw: str | None = Field(default=None, max_length=RAW_MAX)

    @model_validator(mode="after")
    def _raw_only_when_invalid(self) -> "Prediction":
        if self.raw is not None and not self.invalid:
            raise ValueError("raw is allowed only when invalid=true")
        return self


def read_predictions(path: Path | str) -> list[Prediction]:
    with Path(path).open(encoding="utf-8") as fh:
        return [Prediction.model_validate_json(line) for line in fh if line.strip()]


def write_predictions(path: Path | str, preds: list[Prediction]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in preds:
            fh.write(json.dumps(p.model_dump(exclude_defaults=True), ensure_ascii=False) + "\n")


def normalize_label(task: TaskName, value):
    """RuMedTest answers may come as '3' or 3."""
    if task is TaskName.TEST and isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return value


def _check_value(task: TaskName, pred: Prediction, example) -> str | None:
    value = normalize_label(task, pred.prediction)
    if task in LABELS:
        if isinstance(value, list) or value not in LABELS[task]:
            return f"{pred.id}: недопустимое значение {value!r}, ожидается одно из {sorted(LABELS[task], key=str)}"
        return None
    if task in (TaskName.TOP3, TaskName.SYMPTOM_REC):
        if not isinstance(value, list) or len(value) != 3 or len(set(value)) != 3 or not all(
            isinstance(v, str) and v for v in value
        ):
            return f"{pred.id}: нужен список из ровно 3 различных меток, получено {value!r}"
        return None
    if task is TaskName.NER:
        assert isinstance(example, NERExample)
        if not isinstance(value, list) or len(value) != len(example.tokens):
            n = len(value) if isinstance(value, list) else "не список"
            return f"{pred.id}: длина тегов {n} != числу токенов {len(example.tokens)}"
        unknown = sorted(set(value) - NER_TAGS)
        if unknown:
            return f"{pred.id}: неизвестные теги {unknown}"
        return None
    return f"{pred.id}: неизвестная задача {task}"


def validate_predictions(
    task: TaskName | str, role: Role | str, preds: list[Prediction], config: DataConfig | None = None
) -> dict[str, Prediction]:
    """Check predictions cover the role exactly once with valid values; return them by id."""
    task, role = TaskName(task), Role(role)
    examples = {e.id: e for e in get_role(task, role, config)}
    problems: list[str] = []
    counts = Counter(p.id for p in preds)
    problems += [f"{i}: дубликат ({n} раз)" for i, n in counts.items() if n > 1]
    problems += [f"{i}: лишний id (нет в роли {role})" for i in counts if i not in examples]
    problems += [f"{i}: нет предсказания" for i in examples if i not in counts]
    by_id = {p.id: p for p in preds}
    for pid, pred in by_id.items():
        if pid in examples:
            problem = _check_value(task, pred, examples[pid])
            if problem:
                problems.append(problem)
    if problems:
        raise PredictionError(task, problems)
    return by_id
