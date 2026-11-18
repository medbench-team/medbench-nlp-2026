import pytest

from medbench.data import get_role
from medbench.eval.errors import PredictionError
from medbench.eval.predictions import Prediction, read_predictions, validate_predictions, write_predictions


def gold_preds(task, role, config):
    out = []
    for e in get_role(task, role, config):
        if task == "RuMedNER":
            out.append(Prediction(id=e.id, prediction=list(e.tags)))
        elif task in ("RuMedTop3", "RuMedSymptomRec"):
            out.append(Prediction(id=e.id, prediction=[e.label, "x1", "x2"]))
        else:
            out.append(Prediction(id=e.id, prediction=e.label))
    return out


@pytest.mark.parametrize("task", ["RuMedNLI", "RuMedDaNet", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"])
def test_valid_predictions_pass(downloaded_config, task):
    preds = gold_preds(task, "tune", downloaded_config)
    assert len(validate_predictions(task, "tune", preds, downloaded_config)) == len(preds)


def test_missing_extra_duplicate(downloaded_config):
    preds = gold_preds("RuMedNLI", "tune", downloaded_config)
    broken = preds[1:] + [preds[1], Prediction(id="ghost", prediction="neutral")]
    with pytest.raises(PredictionError) as info:
        validate_predictions("RuMedNLI", "tune", broken, downloaded_config)
    text = str(info.value)
    assert preds[0].id in text and "нет предсказания" in text
    assert "ghost" in text and "дубликат" in text
    assert info.value.total == 3


@pytest.mark.parametrize(
    ("task", "bad"),
    [
        ("RuMedNLI", "maybe"),
        ("RuMedDaNet", "yes"),
        ("RuMedTop3", ["A", "B"]),
        ("RuMedTop3", ["A", "A", "B"]),
        ("RuMedNER", ["O"]),
    ],
)
def test_invalid_values(downloaded_config, task, bad):
    preds = gold_preds(task, "tune", downloaded_config)
    preds[0] = Prediction(id=preds[0].id, prediction=bad)
    with pytest.raises(PredictionError, match=preds[0].id):
        validate_predictions(task, "tune", preds, downloaded_config)


def test_ner_unknown_tag(downloaded_config):
    preds = gold_preds("RuMedNER", "tune", downloaded_config)
    tags = list(preds[0].prediction)
    tags[0] = "B-Disease"
    preds[0] = Prediction(id=preds[0].id, prediction=tags)
    with pytest.raises(PredictionError, match="B-Disease"):
        validate_predictions("RuMedNER", "tune", preds, downloaded_config)


def test_rumedtest_accepts_string_digits(downloaded_config):
    preds = [Prediction(id=e.id, prediction=str((i % 4) + 1)) for i, e in enumerate(get_role("RuMedTest", "submit", downloaded_config))]
    assert validate_predictions("RuMedTest", "submit", preds, downloaded_config)


def test_raw_only_with_invalid():
    with pytest.raises(ValueError):
        Prediction(id="a", prediction="да", raw="text")
    assert Prediction(id="a", prediction="да", invalid=True, raw="не знаю").invalid


def test_roundtrip(tmp_path):
    preds = [Prediction(id="a", prediction=["B-ADR", "O"]), Prediction(id="b", prediction="да", invalid=True, raw="?")]
    write_predictions(tmp_path / "p.jsonl", preds)
    assert read_predictions(tmp_path / "p.jsonl") == preds
