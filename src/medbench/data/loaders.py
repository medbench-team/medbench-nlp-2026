"""JSONL → unified Example models, with task/file/line in every error."""

import json
from pathlib import Path

from pydantic import ValidationError

from medbench.data.config import DataConfig, default_config
from medbench.data.errors import DataNotFoundError, SchemaError
from medbench.data.schemas import Example, SourceSplit, TaskName, parse_raw


def _describe(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors())


def read_jsonl(path: Path | str, task: TaskName | str, split: SourceSplit | str) -> list[Example]:
    """Parse and validate a source JSONL file. Raises SchemaError on the first bad line."""
    path, task = Path(path), TaskName(task)
    if not path.is_file():
        raise DataNotFoundError(path)
    examples: list[Example] = []
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SchemaError(task, path, line_no, f"некорректный JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise SchemaError(task, path, line_no, "строка не является JSON-объектом")
            try:
                example = parse_raw(task, split, row)
            except KeyError as exc:
                raise SchemaError(task, path, line_no, f"нет поля {exc.args[0]!r}") from exc
            except ValidationError as exc:
                raise SchemaError(task, path, line_no, _describe(exc)) from exc
            if example.id in seen:
                raise SchemaError(task, path, line_no, f"дубликат id {example.id!r} (строка {seen[example.id]})")
            seen[example.id] = line_no
            examples.append(example)
    return examples


def load_split(
    task: TaskName | str, split: SourceSplit | str, config: DataConfig | None = None
) -> list[Example]:
    """Load one downloaded open split. Never touches the network."""
    config = config or default_config()
    spec = config.file(task, split)
    if spec is None:
        raise DataNotFoundError(f"{TaskName(task)}/{SourceSplit(split)} (нет такого сплита в конфиге)")
    return read_jsonl(config.local_path(spec), spec.task, spec.split)
