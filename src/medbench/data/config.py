"""Reading `configs/data.yaml` (data-model.md: Source manifest)."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from medbench.data.schemas import SourceSplit, TaskName

DEFAULT_CONFIG = Path("configs/data.yaml")


class SourceSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo: str
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_url: str


class FileSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    task: TaskName
    split: SourceSplit
    path: str  # path inside the source repository, e.g. data/RuMedNLI/train_v1.jsonl
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rows: int = Field(gt=0)


class DataConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceSpec
    data_dir: Path
    site_dir: Path | None = None
    files: tuple[FileSpec, ...]
    # Rows of train/tune that duplicate a `final` example in the official splits (ADR-014).
    # They are removed from train/tune; any other count is treated as new leakage.
    known_overlaps: dict[TaskName, dict[str, int]] = Field(default_factory=dict)
    root: Path = Path(".")  # directory that relative data_dir / site_dir are resolved against

    @property
    def commit_dir(self) -> Path:
        return self._resolve(self.data_dir) / self.source.commit

    @property
    def site_path(self) -> Path | None:
        return self._resolve(self.site_dir) if self.site_dir is not None else None

    @property
    def tasks(self) -> tuple[TaskName, ...]:
        return tuple(dict.fromkeys(f.task for f in self.files))

    def local_path(self, spec: FileSpec) -> Path:
        return self.commit_dir / spec.task / Path(spec.path).name

    def url(self, spec: FileSpec) -> str:
        return f"{self.source.base_url.rstrip('/')}/{self.source.commit}/{spec.path}"

    def file(self, task: TaskName | str, split: SourceSplit | str) -> FileSpec | None:
        task, split = TaskName(task), SourceSplit(split)
        return next((f for f in self.files if f.task == task and f.split == split), None)

    def splits(self, task: TaskName | str) -> tuple[SourceSplit, ...]:
        task = TaskName(task)
        return tuple(f.split for f in self.files if f.task == task)

    def _resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else self.root / path


def load_config(path: Path | str = DEFAULT_CONFIG) -> DataConfig:
    """Load a data config. Relative paths inside it resolve against the repo root (configs/..)."""
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw.setdefault("root", path.parent.parent)
    return DataConfig.model_validate(raw)


@lru_cache(maxsize=4)
def default_config() -> DataConfig:
    return load_config(DEFAULT_CONFIG)
