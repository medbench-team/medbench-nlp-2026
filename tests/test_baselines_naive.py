from collections import Counter

import pytest

from medbench.baselines.naive import NaiveBaseline
from medbench.data import get_role
from medbench.eval import validate_predictions


def fitted(task, config):
    b = NaiveBaseline()
    b.fit(task, get_role(task, "train", config) if task != "RuMedTest" else [])
    return b


def test_nli_first_of_tied_classes(downloaded_config):
    preds = fitted("RuMedNLI", downloaded_config).predict("RuMedNLI", get_role("RuMedNLI", "tune", downloaded_config))
    train = get_role("RuMedNLI", "train", downloaded_config)
    assert {p.prediction for p in preds} == {Counter(e.label for e in train).most_common()[0][0]}


def test_danet_constant(downloaded_config):
    preds = fitted("RuMedDaNet", downloaded_config).predict("RuMedDaNet", get_role("RuMedDaNet", "tune", downloaded_config))
    assert len({p.prediction for p in preds}) == 1


@pytest.mark.parametrize("task", ["RuMedTop3", "RuMedSymptomRec"])
def test_top3_most_frequent(downloaded_config, task):
    train = get_role(task, "train", downloaded_config)
    preds = fitted(task, downloaded_config).predict(task, get_role(task, "tune", downloaded_config))
    expected = [label for label, _ in Counter(e.label for e in train).most_common(3)]
    assert all(p.prediction == expected for p in preds)
    assert len(set(expected)) == 3


def test_ner_token_lookup(downloaded_config):
    train = get_role("RuMedNER", "train", downloaded_config)
    b = fitted("RuMedNER", downloaded_config)
    ex = train[0]
    assert b.predict("RuMedNER", [ex])[0].prediction == [b._ner_lookup[t] for t in ex.tokens]
    unknown = ex.model_copy(update={"tokens": ("зюзюкабра",), "tags": ("O",)})
    assert b.predict("RuMedNER", [unknown])[0].prediction == ["O"]


def test_rumedtest_first_option(downloaded_config):
    preds = fitted("RuMedTest", downloaded_config).predict("RuMedTest", get_role("RuMedTest", "submit", downloaded_config))
    assert {p.prediction for p in preds} == {1}
    validate_predictions("RuMedTest", "submit", preds, downloaded_config)


@pytest.mark.parametrize("task", ["RuMedNLI", "RuMedDaNet", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"])
def test_predictions_are_valid(downloaded_config, task):
    examples = get_role(task, "tune", downloaded_config)
    validate_predictions(task, "tune", fitted(task, downloaded_config).predict(task, examples), downloaded_config)
