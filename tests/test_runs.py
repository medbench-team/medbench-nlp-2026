import json

import pytest

from medbench.data import get_role
from medbench.data.config import load_config
from medbench.eval.errors import EvalUnavailableError, FinalRunExistsError, StaleRunError
from medbench.eval.predictions import Prediction
from medbench.eval.runs import config_hash, list_runs, load_run, rescore, save_run
from medbench.eval.scoring import score


def nli_preds(config, role="tune", invalid_first=False):
    preds = [Prediction(id=e.id, prediction="neutral") for e in get_role("RuMedNLI", role, config)]
    if invalid_first:
        preds[0] = Prediction(id=preds[0].id, prediction="neutral", invalid=True, raw="не уверен")
    return preds


def test_config_hash_is_canonical():
    assert config_hash("llm", "m", {"a": 1, "b": 2}) == config_hash("llm", "m", {"b": 2, "a": 1})
    assert config_hash("llm", "m", {"a": 1}) != config_hash("llm", "m", {"a": 2})


def test_save_creates_files_and_meta(downloaded_config, tmp_path):
    run = save_run("RuMedNLI", "tune", nli_preds(downloaded_config, invalid_first=True), approach="naive", model="-",
                   params={"label": "neutral"}, usage={"input_tokens": 10}, config=downloaded_config, results_dir=tmp_path)
    assert (run.path / "preds.jsonl").is_file()
    meta = json.loads((run.path / "meta.json").read_text(encoding="utf-8"))
    for key in ("run_id", "approach", "model", "params", "config_hash", "task", "role", "n_examples", "metrics",
                "invalid_rate", "usage", "code_commit", "data_commit", "created_at"):
        assert key in meta
    assert meta["data_commit"] == downloaded_config.source.commit
    assert meta["invalid_rate"] == pytest.approx(1 / len(run.predictions))
    assert "acc" in meta["metrics"]
    assert run.meta.run_id.endswith(f"_naive_RuMedNLI_tune_{run.meta.config_hash[:8]}")


def test_submit_has_no_metrics(downloaded_config, tmp_path):
    preds = [Prediction(id=e.id, prediction="да") for e in get_role("RuMedDaNet", "submit", downloaded_config)]
    run = save_run("RuMedDaNet", "submit", preds, approach="naive", model="-", config=downloaded_config, results_dir=tmp_path)
    assert run.meta.metrics is None
    assert rescore(run.path, downloaded_config) == (None, None)


def test_one_final_per_config(downloaded_config, tmp_path):
    kw = dict(approach="naive", model="-", config=downloaded_config, results_dir=tmp_path)
    save_run("RuMedNLI", "final", nli_preds(downloaded_config, "final"), **kw)
    with pytest.raises(FinalRunExistsError, match="--justification"):
        save_run("RuMedNLI", "final", nli_preds(downloaded_config, "final"), **kw)
    again = save_run("RuMedNLI", "final", nli_preds(downloaded_config, "final"), justification="баг в парсере", **kw)
    assert again.meta.justification == "баг в парсере"
    # another task or another config is independent
    save_run("RuMedNLI", "final", nli_preds(downloaded_config, "final"), approach="naive", model="-",
             params={"v": 2}, config=downloaded_config, results_dir=tmp_path)
    assert len([m for m in list_runs(tmp_path) if m.role == "final"]) == 3


def test_rescore_matches(downloaded_config, tmp_path):
    run = save_run("RuMedNLI", "tune", nli_preds(downloaded_config), approach="naive", model="-",
                   config=downloaded_config, results_dir=tmp_path)
    stored, recomputed = rescore(run.path, downloaded_config)
    assert stored == recomputed


def test_stale_run(downloaded_config, tmp_path, config_path):
    run = save_run("RuMedNLI", "tune", nli_preds(downloaded_config), approach="naive", model="-",
                   config=downloaded_config, results_dir=tmp_path)
    meta = json.loads((run.path / "meta.json").read_text(encoding="utf-8"))
    meta["data_commit"] = "f" * 40
    (run.path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(StaleRunError):
        load_run(run.path, load_config(config_path))


def test_score_refuses_rumedtest_and_submit(downloaded_config):
    with pytest.raises(EvalUnavailableError, match="RuMedTest"):
        score("RuMedTest", [], "submit", downloaded_config)
    with pytest.raises(EvalUnavailableError):
        score("RuMedNLI", nli_preds(downloaded_config, "submit"), "submit", downloaded_config)
