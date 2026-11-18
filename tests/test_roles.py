import shutil

import pytest

from medbench.data import default_config, fingerprint
from medbench.data.config import load_config
from medbench.data.download import download_all
from medbench.data.errors import LeakageError, RoleUnavailableError
from medbench.data.roles import ROLE_TABLE, get_role

from .conftest import FIXTURES, write_config

LABELLED = ["RuMedNLI", "RuMedDaNet"]
EXTENDED = ["RuMedNER", "RuMedTop3", "RuMedSymptomRec"]


@pytest.mark.parametrize("task", LABELLED)
@pytest.mark.parametrize(
    ("role", "split"), [("train", "train"), ("tune", "dev"), ("final", "test"), ("submit", "private_test")]
)
def test_core_roles(downloaded_config, task, role, split):
    examples = get_role(task, role, downloaded_config)
    assert examples and {ex.split for ex in examples} == {split}


@pytest.mark.parametrize("task", EXTENDED)
@pytest.mark.parametrize(("role", "split"), [("train", "train"), ("tune", "dev"), ("final", "test")])
def test_extended_roles(downloaded_config, task, role, split):
    assert {ex.split for ex in get_role(task, role, downloaded_config)} == {split}


@pytest.mark.parametrize("task", EXTENDED)
def test_extended_tasks_have_no_submit(downloaded_config, task):
    with pytest.raises(RoleUnavailableError, match="submit"):
        get_role(task, "submit", downloaded_config)


@pytest.mark.parametrize("role", ["train", "tune", "final"])
def test_rumedtest_only_submit(downloaded_config, role):
    with pytest.raises(RoleUnavailableError, match="RuMedTest: размеченных данных нет, доступна только роль submit"):
        get_role("RuMedTest", role, downloaded_config)
    assert get_role("RuMedTest", "submit", downloaded_config)


def test_role_table_matches_data_model():
    assert ROLE_TABLE["RuMedNLI"] == {"train": "train", "tune": "dev", "final": "test", "submit": "private_test"}
    assert ROLE_TABLE["RuMedTest"] == {"submit": "private_test"}
    assert "submit" not in ROLE_TABLE["RuMedNER"]


def test_leakage_is_an_error_not_silent_filtering(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / "rumedbench", repo)
    dev = repo / "data/RuMedNLI/dev_v1.jsonl"
    test_line = (repo / "data/RuMedNLI/test_v1.jsonl").read_text(encoding="utf-8").splitlines()[0]
    leaked = test_line.replace('"pairID": "', '"pairID": "leak-')
    dev.write_text(dev.read_text(encoding="utf-8") + leaked + "\n", encoding="utf-8")
    config = load_config(write_config(tmp_path, repo))
    download_all(config)
    with pytest.raises(LeakageError, match="1 строк"):
        get_role("RuMedNLI", "tune", config)
    with pytest.raises(LeakageError):
        get_role("RuMedNLI", "final", config)
    assert get_role("RuMedNLI", "submit", config)  # submit is not affected


def test_declared_overlap_is_removed_from_tune_only(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / "rumedbench", repo)
    dev = repo / "data/RuMedNLI/dev_v1.jsonl"
    test_line = (repo / "data/RuMedNLI/test_v1.jsonl").read_text(encoding="utf-8").splitlines()[0]
    dev.write_text(dev.read_text(encoding="utf-8") + test_line.replace('"pairID": "', '"pairID": "dup-') + "\n", encoding="utf-8")
    config = load_config(write_config(tmp_path, repo, known_overlaps={"RuMedNLI": {"tune": 1}}))
    download_all(config)
    tune = get_role("RuMedNLI", "tune", config)
    final = get_role("RuMedNLI", "final", config)
    assert len(tune) == 4 and not any(e.id.startswith("dup-") for e in tune)
    assert len(final) == 4  # official split unchanged
    assert not {fingerprint(e) for e in final} & {fingerprint(e) for e in tune}


# --- real data (US4 / SC-002 / SC-003); skipped when not downloaded --------------------------------

REAL_SIZES = {
    "RuMedNLI": {"train": 11232, "tune": 1393, "final": 1422, "submit": 1536},
    "RuMedDaNet": {"train": 1052, "tune": 256, "final": 256, "submit": 512},
    "RuMedTest": {"submit": 397},
    "RuMedNER": {"train": 3412, "tune": 669, "final": 693},
    "RuMedTop3": {"train": 4690, "tune": 848, "final": 822},
    "RuMedSymptomRec": {"train": 2469, "tune": 415, "final": 415},
}


def _real_config():
    config = default_config()
    if not all(config.local_path(f).is_file() for f in config.files):
        pytest.skip("real data not downloaded: uv run medbench data download")
    return config


@pytest.mark.data
@pytest.mark.parametrize(("task", "role", "size"), [(t, r, n) for t, rs in REAL_SIZES.items() for r, n in rs.items()])
def test_real_role_sizes(task, role, size):
    assert len(get_role(task, role, _real_config())) == size


@pytest.mark.data
@pytest.mark.parametrize("task", ["RuMedNLI", "RuMedDaNet", *EXTENDED])
def test_real_no_leakage(task):
    config = _real_config()
    final = {fingerprint(e) for e in get_role(task, "final", config)}
    seen = {fingerprint(e) for r in ("train", "tune") for e in get_role(task, r, config)}
    assert not final & seen


@pytest.mark.data
def test_real_extended_tasks_content():
    config = _real_config()
    assert all(len(e.tags) == len(e.tokens) for r in ("train", "tune", "final") for e in get_role("RuMedNER", r, config))
    for task in ("RuMedTop3", "RuMedSymptomRec"):
        assert all(e.text.strip() and e.label for e in get_role(task, "final", config))
