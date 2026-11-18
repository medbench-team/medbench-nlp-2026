from pathlib import Path

import pytest

from medbench.baselines.report import build_reproduction_report, render_markdown, write_reproduction_report
from medbench.eval import EvalError
from medbench.eval.runs import RunMeta, config_hash

PREV = Path("configs/previous_art.yaml")
PAPER = {
    "naive": {"RuMedTop3": {"acc": 10.58, "hit3": 22.02}, "RuMedSymptomRec": {"acc": 1.93, "hit3": 5.30},
              "RuMedDaNet": {"acc": 50.0}, "RuMedNLI": {"acc": 33.33}, "RuMedNER": {"acc": 94.31, "f1": 54.24}},
    "linear": {"RuMedTop3": {"acc": 49.5, "hit3": 72.0}, "RuMedSymptomRec": {"acc": 31.6, "hit3": 49.1},
               "RuMedDaNet": {"acc": 51.0}, "RuMedNLI": {"acc": 62.0}, "RuMedNER": {"acc": 94.5, "f1": 63.0}},
}


def write_runs(results_dir: Path):
    base = results_dir / "runs"
    for approach, tasks in PAPER.items():
        h = config_hash(approach, "-", {})
        for i, (task, metrics) in enumerate(tasks.items()):
            rid = f"20261117-00000{i}_{approach}_{task}_final_{h[:8]}"
            meta = RunMeta(run_id=rid, approach=approach, model="-", config_hash=h, task=task, role="final",
                           n_examples=1, metrics=metrics, code_commit="x", data_commit="y",
                           created_at="2026-11-17T00:00:00+00:00")
            (base / rid).mkdir(parents=True)
            (base / rid / "meta.json").write_text(meta.model_dump_json(), encoding="utf-8")


def test_report_table_and_tolerance(tmp_path):
    write_runs(tmp_path)
    report = build_reproduction_report(tmp_path, PREV)
    lines = {(l.approach, l.task, l.metric): l for l in report.lines}
    assert lines[("naive", "RuMedNLI", "acc")].status == "ok"
    assert lines[("naive", "RuMedNER", "f1")].status == "explained"
    assert lines[("linear", "RuMedNLI", "acc")].status == "out"  # 62.0 vs 59.70 → > 1 п.п.
    assert lines[("linear", "RuMedTop3", "acc")].status == "ok"   # 49.5 vs 49.76
    assert ("naive", "Overall", "-") not in lines  # naive NER is explained → overall not judged
    assert lines[("linear", "Overall", "-")].paper == pytest.approx(58.46)
    text = render_markdown(report)
    assert "Причины расхождений" in text and "ADR-014" in text and "ADR-018" in text
    md, js = write_reproduction_report(report, tmp_path / "out")
    assert md.is_file() and js.is_file()


def test_no_final_runs(tmp_path):
    with pytest.raises(EvalError, match="baselines run --role final"):
        build_reproduction_report(tmp_path, PREV)
