"""Naive baseline restored from the official code/naive predictions (research.md R2, ADR-018)."""

from collections import Counter, defaultdict
from typing import Any

from medbench.data import Example, NERExample, TaskName
from medbench.eval import Prediction

CLASSIF = (TaskName.TOP3, TaskName.SYMPTOM_REC)


class NaiveBaseline:
    approach = "naive"
    params: dict[str, Any] = {"strategy": "most_frequent", "ner": "token_lookup", "rumedtest": 1}

    def __init__(self) -> None:
        self._label: dict[TaskName, Any] = {}
        self._ner_lookup: dict[str, str] = {}

    def supports(self, task: TaskName) -> bool:
        return True

    def fit(self, task: TaskName, train: list[Example]) -> None:
        task = TaskName(task)
        if task is TaskName.TEST:
            return  # no training data; always the first option
        if task is TaskName.NER:
            counts: dict[str, Counter] = defaultdict(Counter)
            for e in train:
                assert isinstance(e, NERExample)
                for token, tag in zip(e.tokens, e.tags):
                    counts[token][tag] += 1
            self._ner_lookup = {tok: c.most_common(1)[0][0] for tok, c in counts.items()}
            return
        ranked = [label for label, _ in Counter(e.label for e in train).most_common()]
        # Counter.most_common keeps first-seen order on ties → entailment / да, as in code/naive
        self._label[task] = ranked[:3] if task in CLASSIF else ranked[0]

    def predict(self, task: TaskName, examples: list[Example]) -> list[Prediction]:
        task = TaskName(task)
        if task is TaskName.TEST:
            return [Prediction(id=e.id, prediction=self.params["rumedtest"]) for e in examples]
        if task is TaskName.NER:
            return [Prediction(id=e.id, prediction=[self._ner_lookup.get(t, "O") for t in e.tokens]) for e in examples]
        value = self._label[task]
        return [Prediction(id=e.id, prediction=list(value) if isinstance(value, list) else value) for e in examples]
