"""Baseline protocol and task inputs as in the official code/linear_models (research.md R1)."""

from typing import Any, Protocol

from medbench.data import ClassifExample, DaNetExample, Example, NLIExample, TaskName
from medbench.eval import Prediction


class Baseline(Protocol):
    approach: str
    params: dict[str, Any]

    def supports(self, task: TaskName) -> bool: ...

    def fit(self, task: TaskName, train: list[Example]) -> None: ...

    def predict(self, task: TaskName, examples: list[Example]) -> list[Prediction]: ...


def input_text(example: Example) -> str:
    """Single text fed to TF-IDF: sentence pairs are joined with a space, like the official code."""
    match example:
        case NLIExample():
            return example.premise + " " + example.hypothesis
        case DaNetExample():
            return example.context + " " + example.question
        case ClassifExample():
            return example.text
    raise TypeError(f"no text input for {type(example).__name__}")
