import json
import zipfile

import pytest

from medbench.data import get_role
from medbench.eval.errors import EvalError
from medbench.eval.predictions import Prediction
from medbench.eval.runs import save_run
from medbench.eval.submission import build_submission


def submit_run(task, config, results_dir, value):
    preds = [Prediction(id=e.id, prediction=value) for e in get_role(task, "submit", config)]
    return save_run(task, "submit", preds, approach="naive", model="-", config=config, results_dir=results_dir)


def read_zip(path):
    with zipfile.ZipFile(path) as zf:
        return {n: [json.loads(l) for l in zf.read(n).decode("utf-8").splitlines()] for n in zf.namelist()}


def test_full_submission_format(downloaded_config, tmp_path):
    submit_run("RuMedDaNet", downloaded_config, tmp_path, "нет")
    submit_run("RuMedNLI", downloaded_config, tmp_path, "entailment")
    submit_run("RuMedTest", downloaded_config, tmp_path, 3)
    report = build_submission(results_dir=tmp_path, config=downloaded_config)
    content = read_zip(report.path)
    assert set(content) == {"RuMedDaNet.jsonl", "RuMedNLI.jsonl", "RuMedTest.jsonl"}
    assert set(content["RuMedDaNet.jsonl"][0]) == {"pairID", "answer"}
    assert set(content["RuMedNLI.jsonl"][0]) == {"pairID", "gold_label"}
    assert content["RuMedTest.jsonl"][0] == {"idx": get_role("RuMedTest", "submit", downloaded_config)[0].id, "answer": "3"}
    for name, task in (("RuMedDaNet.jsonl", "RuMedDaNet"), ("RuMedNLI.jsonl", "RuMedNLI")):
        assert [r["pairID"] for r in content[name]] == [e.id for e in get_role(task, "submit", downloaded_config)]
    assert not report.warnings


def test_missing_task_warns_and_naive_fill(downloaded_config, tmp_path):
    submit_run("RuMedNLI", downloaded_config, tmp_path, "neutral")
    report = build_submission(results_dir=tmp_path, config=downloaded_config)
    assert set(read_zip(report.path)) == {"RuMedNLI.jsonl"} and len(report.warnings) == 2
    filled = build_submission(results_dir=tmp_path, naive_fill=True, config=downloaded_config, out_dir=tmp_path / "x")
    content = read_zip(filled.path)
    assert {r["answer"] for r in content["RuMedDaNet.jsonl"]} == {"да"}
    assert {r["answer"] for r in content["RuMedTest.jsonl"]} == {"1"}
    assert filled.sources["RuMedTest"] == "naive"


def test_explicit_non_submit_run_rejected(downloaded_config, tmp_path):
    preds = [Prediction(id=e.id, prediction="neutral") for e in get_role("RuMedNLI", "tune", downloaded_config)]
    run = save_run("RuMedNLI", "tune", preds, approach="naive", model="-", config=downloaded_config, results_dir=tmp_path)
    with pytest.raises(EvalError, match="submit"):
        build_submission(run_ids=[run.meta.run_id], results_dir=tmp_path, config=downloaded_config)


def test_nothing_to_submit(downloaded_config, tmp_path):
    with pytest.raises(EvalError, match="naive-fill"):
        build_submission(results_dir=tmp_path, config=downloaded_config)
