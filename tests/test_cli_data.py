import json

from typer.testing import CliRunner

from medbench.cli import app

from .conftest import FIXTURES, write_config

runner = CliRunner()


def test_download_prints_table(config_path):
    result = runner.invoke(app, ["data", "download", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "RuMedNLI" in result.output and "private_test" in result.output
    assert "site data: found" in result.output


def test_download_twice_skips(config_path):
    runner.invoke(app, ["data", "download", "--config", str(config_path)])
    result = runner.invoke(app, ["data", "download", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "skipped" in result.output


def test_verify_fails_on_broken_file(config_path, config):
    runner.invoke(app, ["data", "download", "--config", str(config_path)])
    path = config.local_path(config.file("RuMedDaNet", "train"))
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[1])
    row["answer"] = "может быть"
    lines[1] = json.dumps(row, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = runner.invoke(app, ["data", "verify", "--config", str(config_path), "--no-check-sha"])
    assert result.exit_code == 1
    assert "RuMedDaNet" in result.output and "строка 2" in result.output and "train_v1.jsonl" in result.output


def test_missing_site_dir_is_a_warning(tmp_path):
    path = write_config(tmp_path, FIXTURES / "rumedbench", site_dir=None)
    result = runner.invoke(app, ["data", "download", "--config", str(path)])
    assert result.exit_code == 0
    assert "site data: not found" in result.output
