"""Evaluation harness (contracts/eval-api.md): metrics as in the official RuMedBench eval.py,
run registry, leaderboard and medbench.ru submission. Approaches save results only via `save_run`.
"""

from medbench.eval.errors import (
    EvalError,
    EvalUnavailableError,
    FinalRunExistsError,
    PredictionError,
    StaleRunError,
)
from medbench.eval.leaderboard import build_leaderboard, write_leaderboard
from medbench.eval.metrics import TaskMetrics, overall
from medbench.eval.predictions import Prediction, read_predictions, validate_predictions, write_predictions
from medbench.eval.runs import Run, RunMeta, config_hash, list_runs, load_run, rescore, save_run
from medbench.eval.scoring import score
from medbench.eval.submission import build_submission

__all__ = [
    "EvalError",
    "EvalUnavailableError",
    "FinalRunExistsError",
    "Prediction",
    "PredictionError",
    "Run",
    "RunMeta",
    "StaleRunError",
    "TaskMetrics",
    "build_leaderboard",
    "build_submission",
    "config_hash",
    "list_runs",
    "load_run",
    "overall",
    "read_predictions",
    "rescore",
    "save_run",
    "score",
    "validate_predictions",
    "write_leaderboard",
    "write_predictions",
]
