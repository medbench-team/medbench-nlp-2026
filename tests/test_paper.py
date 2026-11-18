import json

import pytest

from medbench.data.errors import DataError
from medbench.eval.paper import metrics_from_official_file, reproduce_paper


def test_official_format_parsing(fixtures_dir):
    d = fixtures_dir / "paper"
    for task in ("RuMedTop3", "RuMedNER", "RuMedNLI", "RuMedDaNet"):
        m = metrics_from_official_file(task, d / f"{task}.jsonl")
        assert 0 <= m.acc <= 100
    top3 = metrics_from_official_file("RuMedTop3", d / "RuMedTop3.jsonl")
    rows = [json.loads(l) for l in (d / "RuMedTop3.jsonl").read_text(encoding="utf-8").splitlines()]
    assert top3.acc == pytest.approx(100 * sum(r["code"] == r["prediction"][0] for r in rows) / len(rows))
    assert metrics_from_official_file("RuMedNER", d / "RuMedNER.jsonl").f1 is not None


@pytest.mark.data
def test_reproduces_paper_table():
    try:
        results = reproduce_paper()
    except DataError as exc:  # no network
        pytest.skip(f"network unavailable: {exc}")
    assert {r.paper_row for r in results} == {"Naive", "TF-IDF", "BiLSTM", "RuPoolBERT", "Human"}
    for r in results:
        assert not r.mismatches, (r.name, r.mismatches)
