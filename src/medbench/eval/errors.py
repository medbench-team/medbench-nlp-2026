"""Evaluation-layer exceptions (Russian messages)."""

MAX_SHOWN = 20


class EvalError(Exception):
    """Base class for evaluation errors."""


class PredictionError(EvalError):
    """Predictions do not match the role: missing / extra / duplicate ids or invalid values."""

    def __init__(self, task: str, problems: list[str]):
        self.task, self.problems, self.total = str(task), problems, len(problems)
        shown = "\n  - ".join(problems[:MAX_SHOWN])
        more = f"\n  … и ещё {self.total - MAX_SHOWN}" if self.total > MAX_SHOWN else ""
        super().__init__(f"{self.task}: предсказания не прошли проверку ({self.total} проблем):\n  - {shown}{more}")


class EvalUnavailableError(EvalError):
    """Local evaluation is impossible (RuMedTest, role submit/train)."""


class FinalRunExistsError(EvalError):
    """A `final` run already exists for this (config_hash, task) — constitution principle I."""


class StaleRunError(EvalError):
    """The run was produced on a different data version (data_commit)."""
