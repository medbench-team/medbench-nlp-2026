import json

from medbench.data.stats import PAPER_SIZES, build_stats, write_stats


def test_stats_on_fixtures(downloaded_config, tmp_path):
    stats = build_stats(downloaded_config)
    assert set(stats.tasks) == {"RuMedNLI", "RuMedDaNet", "RuMedTest", "RuMedNER", "RuMedTop3", "RuMedSymptomRec"}
    nli = stats.tasks["RuMedNLI"]
    assert nli["splits"]["train"]["rows"] == 4
    assert sum(nli["splits"]["train"]["labels"].values()) == 4
    assert nli["splits"]["private_test"]["labels"] == {}
    lengths = nli["splits"]["dev"]["length_words"]
    assert lengths["min"] <= lengths["median"] <= lengths["p95"] <= lengths["max"]
    assert stats.tasks["RuMedNER"]["splits"]["train"]["labels"]  # entity types counted
    assert stats.tasks["RuMedTop3"]["splits"]["train"]["n_classes"] >= 1
    assert nli["examples"], "one or two examples per task"
    # fixtures are tiny → every split differs from the paper sizes and the report says so
    assert stats.paper_mismatches

    md, js, pngs = write_stats(stats, tmp_path / "out")
    text = md.read_text(encoding="utf-8")
    for task in stats.tasks:
        assert f"## {task}" in text
    assert json.loads(js.read_text(encoding="utf-8"))["tasks"]["RuMedNLI"]["splits"]["train"]["rows"] == 4
    assert len(pngs) == 6 and all(p.stat().st_size > 0 for p in pngs)


def test_paper_sizes_cover_core_tasks():
    assert PAPER_SIZES["RuMedNLI"] == {"train": 11232, "dev": 1395, "test": 1422}
    assert PAPER_SIZES["RuMedDaNet"] == {"train": 1052, "dev": 256, "test": 256}
