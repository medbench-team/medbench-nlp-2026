import pytest

from medbench.eval.metrics import (
    TaskMetrics,
    accuracy,
    hit_at_3,
    ner_entities,
    ner_f1,
    ner_token_accuracy,
    overall,
)


def test_accuracy():
    assert accuracy(["a", "b", "c", "d"], ["a", "x", "c", "d"]) == 75.0
    with pytest.raises(ValueError):
        accuracy(["a"], ["a", "b"])


def test_hit_at_3_uses_set_membership():
    gold = ["A", "B", "C"]
    top3 = [["A", "x", "y"], ["x", "y", "B"], ["x", "y", "z"]]
    assert hit_at_3(gold, top3) == pytest.approx(200 / 3)
    assert accuracy(gold, [t[0] for t in top3]) == pytest.approx(100 / 3)


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (["B-ADR", "I-ADR", "O"], {("ADR", 0, 1)}),
        (["O", "I-DI", "I-DI"], {("DI", 1, 2)}),  # I- after O starts an entity (lenient)
        (["B-DI", "I-ADR"], {("DI", 0, 0), ("ADR", 1, 1)}),  # type change starts a new entity
        (["O", "B-Drugname"], {("Drugname", 1, 1)}),  # entity at the very end
        (["B-DI", "B-DI"], {("DI", 0, 0), ("DI", 1, 1)}),  # adjacent B-
        (["I-ADR", "B-ADR", "I-ADR"], {("ADR", 0, 0), ("ADR", 1, 2)}),
        (["O", "O"], set()),
    ],
)
def test_ner_entities_lenient_iob(tags, expected):
    assert ner_entities(tags) == expected


def test_ner_f1_micro_over_sentences():
    gold = [["B-DI", "I-DI", "O"], ["B-ADR", "O", "B-Drugname"]]
    pred = [["B-DI", "I-DI", "O"], ["B-ADR", "B-Drugname", "O"]]
    # gold entities: 3, pred: 3, tp: 2 → P = R = 2/3 → F1 = 66.67
    assert ner_f1(gold, pred) == pytest.approx(200 / 3)
    assert ner_token_accuracy(gold, pred) == pytest.approx(100 * 4 / 6)


def test_ner_f1_no_predictions():
    assert ner_f1([["B-DI"]], [["O"]]) == 0.0


def test_task_metrics_score_and_overall():
    per_task = {
        "RuMedTop3": TaskMetrics(acc=40, hit3=60),
        "RuMedSymptomRec": TaskMetrics(acc=20, hit3=40),
        "RuMedDaNet": TaskMetrics(acc=70),
        "RuMedNLI": TaskMetrics(acc=80),
        "RuMedNER": TaskMetrics(acc=96, f1=74),
    }
    assert per_task["RuMedTop3"].score == 50
    assert overall(per_task) == pytest.approx((50 + 30 + 70 + 80 + 85) / 5)
    del per_task["RuMedNER"]
    assert overall(per_task) is None
