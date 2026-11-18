import json
import shutil

from medbench.data.config import load_config
from medbench.data.download import download_all
from medbench.data.overlap import build_overlap_report, write_overlap_report

from .conftest import FIXTURES, write_config


def test_site_fixture_matrix(downloaded_config):
    report = build_overlap_report(downloaded_config)
    nli = report.pairs["RuMedNLI"]
    assert nli["site:train"]["open:train"] == 4 and nli["site:train"]["open:dev"] == 4
    assert nli["site:train"]["open:test"] == 0
    assert nli["site:dev"]["open:test"] == 4 and nli["site:dev"]["open:dev"] == 0
    assert nli["site:test"]["open:private_test"] == 4
    assert report.pairs["RuMedTest"]["site:test"]["open:private_test"] == 4
    assert ("RuMedNLI", "test") in report.identical_files
    assert not report.label_conflicts
    assert report.site_found


def test_label_conflict_detected(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(FIXTURES / "site", site)
    dev = site / "RuMedDaNet/dev.jsonl"
    rows = [json.loads(l) for l in dev.read_text(encoding="utf-8").splitlines()]
    rows[0]["answer"] = "нет" if rows[0]["answer"] == "да" else "да"
    dev.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    config = load_config(write_config(tmp_path, FIXTURES / "rumedbench", site_dir=site))
    download_all(config)
    report = build_overlap_report(config)
    assert len(report.label_conflicts) == 1
    assert report.label_conflicts[0]["task"] == "RuMedDaNet"
    assert {report.label_conflicts[0]["a"], report.label_conflicts[0]["b"]} == {"site:dev", "open:test"}


def test_without_site_dir(tmp_path):
    config = load_config(write_config(tmp_path, FIXTURES / "rumedbench", site_dir=None))
    download_all(config)
    report = build_overlap_report(config)
    assert not report.site_found and not report.identical_files
    assert report.open_pairs["RuMedNLI"]["open:test"]["open:train"] == 0


def test_report_files_written(downloaded_config, tmp_path):
    report = build_overlap_report(downloaded_config)
    md, js = write_overlap_report(report, tmp_path / "out")
    text = md.read_text(encoding="utf-8")
    assert "dev сайта" in text and "RuMedNLI" in text
    assert json.loads(js.read_text(encoding="utf-8"))["pairs"]["RuMedNLI"]["site:dev"]["open:test"] == 4
