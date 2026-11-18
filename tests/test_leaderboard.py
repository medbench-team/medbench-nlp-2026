import time
from pathlib import Path

import pytest
import yaml

from medbench.data import get_role
from medbench.eval.leaderboard import build_leaderboard, load_previous_art, render_markdown, write_leaderboard
from medbench.eval.predictions import Prediction
from medbench.eval.runs import save_run

PREV = Path("configs/previous_art.yaml")
TASKS = ["RuMedTop3", "RuMedSymptomRec", "RuMedDaNet", "RuMedNLI", "RuMedNER"]


def gold(task, role, config):
    out = []
    for e in get_role(task, role, config):
        if task == "RuMedNER":
            out.append(Prediction(id=e.id, prediction=list(e.tags)))
        elif task in ("RuMedTop3", "RuMedSymptomRec"):
            out.append(Prediction(id=e.id, prediction=[e.label, "z1", "z2"]))
        else:
            out.append(Prediction(id=e.id, prediction=e.label))
    return out


@pytest.fixture
def results(downloaded_config, tmp_path):
    kw = dict(config=downloaded_config, results_dir=tmp_path)
    for t in TASKS:  # "oracle" approach with all 5 tasks on final → Overall present
        save_run(t, "final", gold(t, "final", downloaded_config), approach="oracle", model="-", **kw)
    save_run("RuMedNLI", "final", gold("RuMedNLI", "final", downloaded_config), approach="oracle", model="-",
             justification="перезапуск после фикса", **kw)
    save_run("RuMedNLI", "final", [Prediction(id=e.id, prediction="neutral") for e in get_role("RuMedNLI", "final", downloaded_config)],
             approach="naive", model="-", **kw)  # partial → Overall "—"
    save_run("RuMedDaNet", "tune", gold("RuMedDaNet", "tune", downloaded_config), approach="oracle", model="-", **kw)
    return tmp_path


def test_tables_are_separated(results):
    lb = build_leaderboard(results, PREV)
    assert {r.system.split(" · ")[0] for r in lb.final} == {"oracle", "naive"}
    assert [r.system.split(" · ")[0] for r in lb.tune] == ["oracle"]
    assert any(r.system == "RuBioRoBERTa" for r in lb.previous_open)
    assert [r.system for r in lb.site] == ["ChatGPT (text-davinci-003)"]


def test_overall_only_for_complete_sets(results):
    lb = build_leaderboard(results, PREV)
    rows = {r.system.split(" · ")[0]: r for r in lb.final}
    assert rows["oracle"].overall == pytest.approx(100.0)
    assert rows["naive"].overall is None


def test_best_previous_excludes_human_and_site(results):
    lb = build_leaderboard(results, PREV)
    assert lb.best_previous["RuMedDaNet"] == pytest.approx(76.17)
    assert lb.best_previous["RuMedNLI"] == pytest.approx(82.77)


def test_markdown_marks_sota_delta_and_justification(results):
    text = render_markdown(build_leaderboard(results, PREV))
    assert "★" in text and "(+" in text
    assert "†" in text and "перезапуск после фикса" in text
    assert "## Закрытый test сайта" in text and "89.30" in text
    assert "**100.00**" in text


def test_write_files(results):
    md, js = write_leaderboard(build_leaderboard(results, PREV), results)
    assert md.is_file() and js.is_file()


def test_previous_art_validation(tmp_path):
    bad = [{"system": "X", "source": "s", "test": "open", "metrics": {"RuMedNLI": {"f1": 1.0}}}]
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        load_previous_art(path)
    assert len(load_previous_art(PREV)) == 9


def test_leaderboard_speed(results):
    start = time.perf_counter()
    for _ in range(10):
        build_leaderboard(results, PREV)
    assert time.perf_counter() - start < 10
