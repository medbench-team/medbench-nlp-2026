"""TF-IDF (char 3–8) + one-vs-rest LogReg C=10, and CRF for NER — hyperparameters of code/linear_models
(research.md R1, R3, R4; ADR-019)."""

import random
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pycrfsuite
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

from medbench.baselines.base import input_text
from medbench.data import Example, NERExample, TaskName
from medbench.eval import Prediction

TOP3_TASKS = (TaskName.TOP3, TaskName.SYMPTOM_REC)
SEED = 128


def word2features(tokens: tuple[str, ...], i: int) -> dict[str, Any]:
    word = tokens[i]
    features: dict[str, Any] = {
        "bias": 1.0,
        "word.lower()": word.lower(),
        "word[-3:]": word[-3:],
        "word[-2:]": word[-2:],
        "word.isupper()": word.isupper(),
        "word.istitle()": word.istitle(),
        "word.isdigit()": word.isdigit(),
    }
    if i > 0:
        prev = tokens[i - 1]
        features.update({"-1:word.lower()": prev.lower(), "-1:word.istitle()": prev.istitle(),
                         "-1:word.isupper()": prev.isupper()})
    else:
        features["BOS"] = True
    if i < len(tokens) - 1:
        nxt = tokens[i + 1]
        features.update({"+1:word.lower()": nxt.lower(), "+1:word.istitle()": nxt.istitle(),
                         "+1:word.isupper()": nxt.isupper()})
    else:
        features["EOS"] = True
    return features


def sent2features(tokens: tuple[str, ...]) -> list[dict[str, Any]]:
    return [word2features(tokens, i) for i in range(len(tokens))]


class LinearBaseline:
    approach = "linear"
    params: dict[str, Any] = {
        "tfidf": {"analyzer": "char", "ngram_range": [3, 8]},
        "logreg": {"C": 10, "penalty": "l2", "scheme": "ovr", "max_iter": 1000},
        "crf": {"algorithm": "lbfgs", "c1": 0.1, "c2": 0.01, "max_iterations": 200,
                "all_possible_transitions": True, "seed": SEED},
    }

    def __init__(self, n_jobs: int = 2) -> None:
        self.n_jobs = n_jobs
        self._models: dict[TaskName, Any] = {}

    def supports(self, task: TaskName) -> bool:
        return TaskName(task) is not TaskName.TEST

    def fit(self, task: TaskName, train: list[Example]) -> None:
        task = TaskName(task)
        random.seed(SEED)
        np.random.seed(SEED)
        if task is TaskName.NER:
            trainer = pycrfsuite.Trainer(verbose=False)
            for e in train:
                assert isinstance(e, NERExample)
                trainer.append(sent2features(e.tokens), list(e.tags))
            crf = self.params["crf"]
            trainer.set_params({"c1": crf["c1"], "c2": crf["c2"], "max_iterations": crf["max_iterations"],
                                "feature.possible_transitions": crf["all_possible_transitions"]})
            with tempfile.TemporaryDirectory(prefix="medbench-crf-") as tmp:
                path = Path(tmp) / "ner.crfsuite"
                trainer.train(str(path))
                tagger = pycrfsuite.Tagger()
                tagger.open(str(path))  # the model is loaded/mapped; the file may be removed afterwards
            self._models[task] = tagger
            return
        tf, lr = self.params["tfidf"], self.params["logreg"]
        vectorizer = TfidfVectorizer(analyzer=tf["analyzer"], ngram_range=tuple(tf["ngram_range"]))
        X = vectorizer.fit_transform([input_text(e) for e in train])
        clf = OneVsRestClassifier(LogisticRegression(C=lr["C"], max_iter=lr["max_iter"]),  # L2 is the default
                                  n_jobs=self.n_jobs)
        clf.fit(X, [e.label for e in train])
        self._models[task] = (vectorizer, clf)

    def predict(self, task: TaskName, examples: list[Example]) -> list[Prediction]:
        task = TaskName(task)
        model = self._models[task]
        if task is TaskName.NER:
            return [Prediction(id=e.id, prediction=model.tag(sent2features(e.tokens))) for e in examples]
        vectorizer, clf = model
        X = vectorizer.transform([input_text(e) for e in examples])
        if task in TOP3_TASKS:
            proba = clf.predict_proba(X)
            top = np.argsort(-proba, axis=1, kind="stable")[:, :3]
            return [Prediction(id=e.id, prediction=[str(clf.classes_[j]) for j in row]) for e, row in zip(examples, top)]
        return [Prediction(id=e.id, prediction=str(p)) for e, p in zip(examples, clf.predict(X))]
