from medbench.baselines.runner import run_baselines
from medbench.eval import list_runs

ALL = ["RuMedNLI", "RuMedDaNet", "RuMedTest", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"]


def test_default_tune_only(downloaded_config, tmp_path):
    out = run_baselines(["naive"], ALL, ["tune"], config=downloaded_config, results_dir=tmp_path)
    saved = [o for o in out if o.status == "saved"]
    assert {o.role for o in saved} == {"tune"} and len(saved) == 5
    skipped = [o for o in out if o.status == "skipped"]
    assert [(o.task, o.role) for o in skipped] == [("RuMedTest", "tune")]
    assert {m.role for m in list_runs(tmp_path)} == {"tune"}


def test_final_once(downloaded_config, tmp_path):
    kw = dict(config=downloaded_config, results_dir=tmp_path)
    first = run_baselines(["naive"], ["RuMedNLI"], ["final"], **kw)
    assert first[0].status == "saved"
    second = run_baselines(["naive"], ["RuMedNLI"], ["final"], **kw)
    assert second[0].status == "skipped" and "justification" in second[0].reason
    third = run_baselines(["naive"], ["RuMedNLI"], ["final"], justification="проверка", **kw)
    assert third[0].status == "saved"


def test_skips(downloaded_config, tmp_path):
    out = run_baselines(["linear"], ["RuMedTest"], ["submit"], config=downloaded_config, results_dir=tmp_path)
    assert out[0].status == "skipped" and "RuMedTest" in out[0].reason
    out = run_baselines(["naive"], ["RuMedNER"], ["submit"], config=downloaded_config, results_dir=tmp_path)
    assert out[0].status == "skipped" and "submit" in out[0].reason
    out = run_baselines(["naive"], ["RuMedTest"], ["submit"], config=downloaded_config, results_dir=tmp_path)
    assert out[0].status == "saved" and out[0].metrics is None


def test_one_config_hash_per_approach(downloaded_config, tmp_path):
    tasks = ["RuMedNLI", "RuMedDaNet", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"]
    run_baselines(["naive", "linear"], tasks, ["tune"], config=downloaded_config, results_dir=tmp_path)
    by_approach = {}
    for m in list_runs(tmp_path):
        by_approach.setdefault(m.approach, set()).add(m.config_hash)
    assert {k: len(v) for k, v in by_approach.items()} == {"naive": 1, "linear": 1}
