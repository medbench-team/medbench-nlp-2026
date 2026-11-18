"""Shared fixtures. Tests never touch the network: the source repo is served via file://."""

import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from medbench.data.config import DataConfig, load_config

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_COMMIT = "0" * 40
FIXTURE_FILES = {
    "RuMedNLI": ["train", "dev", "test", "private_test"],
    "RuMedDaNet": ["train", "dev", "test", "private_test"],
    "RuMedTest": ["private_test"],
    "RuMedNER": ["train", "dev", "test"],
    "RuMedTop3": ["train", "dev", "test"],
    "RuMedSymptomRec": ["train", "dev", "test"],
}


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def _rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def write_config(
    tmp_path: Path,
    repo_dir: Path,
    *,
    site_dir: Path | None = None,
    sha_overrides: dict[tuple[str, str], str] | None = None,
    known_overlaps: dict[str, dict[str, int]] | None = None,
) -> Path:
    """Write a data.yaml pointing at a file:// copy of `repo_dir` (layout: <repo>/data/<Task>/...)."""
    served = tmp_path / "remote"
    if not (served / FAKE_COMMIT).exists():
        shutil.copytree(repo_dir, served / FAKE_COMMIT)
    files = []
    for task, splits in FIXTURE_FILES.items():
        for split in splits:
            rel = f"data/{task}/{split}_v1.jsonl"
            src = served / FAKE_COMMIT / rel
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
            sha = (sha_overrides or {}).get((task, split), sha)
            files.append({"task": task, "split": split, "path": rel, "sha256": sha, "rows": _rows(src)})
    cfg = {
        "source": {"repo": "fixture/MedBench", "commit": FAKE_COMMIT, "base_url": served.as_uri()},
        "data_dir": str(tmp_path / "local"),
        "site_dir": str(site_dir) if site_dir else str(tmp_path / "no-site"),
        "files": files,
        "known_overlaps": known_overlaps or {},
    }
    path = tmp_path / "configs" / "data.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Fixture config with site data available."""
    return write_config(tmp_path, FIXTURES / "rumedbench", site_dir=FIXTURES / "site")


@pytest.fixture
def config(config_path: Path) -> DataConfig:
    return load_config(config_path)


@pytest.fixture
def downloaded_config(config: DataConfig) -> DataConfig:
    """Fixture config with all files already 'downloaded' into the local data dir."""
    from medbench.data.download import download_all

    download_all(config)
    return config
