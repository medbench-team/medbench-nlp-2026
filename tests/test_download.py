import json

import pytest

from medbench.data.config import load_config
from medbench.data.download import download_all, verify_all
from medbench.data.errors import ChecksumError, SchemaError

from .conftest import FIXTURES, FIXTURE_FILES, write_config

N_FILES = sum(len(s) for s in FIXTURE_FILES.values())


def test_download_fetches_and_verifies_all_files(config):
    report = download_all(config)
    assert len(report.downloaded) == N_FILES and not report.skipped
    for spec in config.files:
        assert config.local_path(spec).is_file()
    manifest = json.loads((config.commit_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["commit"] == config.source.commit
    assert len(manifest["files"]) == N_FILES
    assert report.rows[("RuMedNLI", "train")] == 4


def test_second_run_is_idempotent(config):
    download_all(config)
    report = download_all(config)
    assert not report.downloaded
    assert len(report.skipped) == N_FILES


def test_force_redownloads(config):
    download_all(config)
    report = download_all(config, force=True)
    assert len(report.downloaded) == N_FILES


def test_corrupted_local_file_is_redownloaded(config):
    download_all(config)
    spec = config.file("RuMedDaNet", "dev")
    config.local_path(spec).write_text("garbage\n", encoding="utf-8")
    report = download_all(config)
    assert ("RuMedDaNet", "dev") in report.downloaded


def test_checksum_mismatch_fails_and_leaves_no_file(tmp_path):
    path = write_config(tmp_path, FIXTURES / "rumedbench", sha_overrides={("RuMedNLI", "dev"): "f" * 64})
    config = load_config(path)
    with pytest.raises(ChecksumError, match="RuMedNLI"):
        download_all(config)
    assert not config.local_path(config.file("RuMedNLI", "dev")).exists()


def test_verify_detects_schema_error_with_line(downloaded_config):
    spec = downloaded_config.file("RuMedNLI", "train")
    path = downloaded_config.local_path(spec)
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[2])
    del row["ru_sentence1"]
    lines[2] = json.dumps(row, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # sha256 differs → verify reports the checksum first; with check_sha disabled we see the schema error
    with pytest.raises(ChecksumError):
        verify_all(downloaded_config)
    with pytest.raises(SchemaError) as info:
        verify_all(downloaded_config, check_sha=False)
    assert info.value.line == 3 and "ru_sentence1" in str(info.value)


def test_verify_ok(downloaded_config):
    report = verify_all(downloaded_config)
    assert len(report.rows) == N_FILES
