"""Download and verify the pinned open RuMedBench files (FR-001, FR-003, FR-009)."""

import hashlib
import json
import os
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from medbench.data.config import DataConfig, FileSpec
from medbench.data.errors import ChecksumError, DataError, DataNotFoundError, RowCountError
from medbench.data.loaders import read_jsonl

TIMEOUT_S = 60
Key = tuple[str, str]  # (task, split)


@dataclass
class DownloadReport:
    downloaded: list[Key] = field(default_factory=list)
    skipped: list[Key] = field(default_factory=list)
    rows: dict[Key, int] = field(default_factory=dict)


@dataclass
class VerifyReport:
    rows: dict[Key, int] = field(default_factory=dict)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(spec: FileSpec) -> Key:
    return (str(spec.task), str(spec.split))


def _check_file(config: DataConfig, spec: FileSpec, path: Path, *, check_sha: bool = True) -> int:
    """Validate checksum, schema and row count; return number of rows."""
    if check_sha:
        actual = sha256_file(path)
        if actual != spec.sha256:
            raise ChecksumError(path, spec.sha256, actual)
    rows = len(read_jsonl(path, spec.task, spec.split))
    if rows != spec.rows:
        raise RowCountError(path, spec.rows, rows)
    return rows


def fetch_url(url: str, dest: Path) -> None:
    """Download `url` atomically into `dest` (temp file + rename)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(url, timeout=TIMEOUT_S) as resp:
            while chunk := resp.read(1 << 16):
                out.write(chunk)
        os.replace(tmp, dest)
    except OSError as exc:
        Path(tmp).unlink(missing_ok=True)
        raise DataError(f"Не удалось скачать {url}: {exc}") from exc


def _is_verified(spec: FileSpec, path: Path) -> bool:
    return path.is_file() and sha256_file(path) == spec.sha256


def download_all(config: DataConfig, force: bool = False) -> DownloadReport:
    """Download every configured file unless an identical copy is already present."""
    report = DownloadReport()
    manifest_files = {}
    for spec in config.files:
        path = config.local_path(spec)
        if not force and _is_verified(spec, path):
            report.skipped.append(_key(spec))
        else:
            fetch_url(config.url(spec), path)
            try:
                _check_file(config, spec, path)
            except DataError:
                path.unlink(missing_ok=True)
                raise
            report.downloaded.append(_key(spec))
        report.rows[_key(spec)] = spec.rows
        manifest_files[f"{spec.task}/{spec.split}"] = {
            "path": str(path.relative_to(config.commit_dir)),
            "sha256": spec.sha256,
            "rows": spec.rows,
        }
    if report.downloaded or not (config.commit_dir / "manifest.json").exists():
        manifest = {
            "repo": config.source.repo,
            "commit": config.source.commit,
            "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "files": manifest_files,
        }
        (config.commit_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return report


def verify_all(config: DataConfig, check_sha: bool = True) -> VerifyReport:
    """Offline check of every local file: presence, sha256, schema and row count."""
    report = VerifyReport()
    for spec in config.files:
        path = config.local_path(spec)
        if not path.is_file():
            raise DataNotFoundError(path)
        report.rows[_key(spec)] = _check_file(config, spec, path, check_sha=check_sha)
    return report
