import pytest

from medbench.baselines.linear import LinearBaseline
from medbench.data import get_role
from medbench.eval import validate_predictions


@pytest.mark.parametrize("task", ["RuMedNLI", "RuMedDaNet", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"])
def test_fit_predict_valid(downloaded_config, task):
    b = LinearBaseline(n_jobs=1)
    b.fit(task, get_role(task, "train", downloaded_config))
    examples = get_role(task, "tune", downloaded_config)
    preds = b.predict(task, examples)
    validate_predictions(task, "tune", preds, downloaded_config)
    if task in ("RuMedTop3", "RuMedSymptomRec"):
        assert all(len(set(p.prediction)) == 3 for p in preds)
    if task == "RuMedNER":
        assert [len(p.prediction) for p in preds] == [len(e.tokens) for e in examples]


def test_rumedtest_not_supported():
    assert LinearBaseline().supports("RuMedTest") is False


def test_params_shared_across_tasks():
    assert LinearBaseline().params == LinearBaseline().params
    assert LinearBaseline.params["tfidf"]["ngram_range"] == [3, 8]
    assert LinearBaseline.params["logreg"]["C"] == 10
