"""`medbench data …` commands (contracts/cli.md)."""

from pathlib import Path
from typing import Annotated

import typer

from medbench.data.config import DEFAULT_CONFIG, DataConfig, load_config
from medbench.data.errors import DataError
from medbench.data.schemas import SourceSplit

data_app = typer.Typer(help="RuMedBench data: download, verify, overlap, stats.", no_args_is_help=True)

ConfigOpt = Annotated[Path, typer.Option("--config", help="Path to data config (YAML).")]


def _load(config_path: Path) -> DataConfig:
    try:
        return load_config(config_path)
    except (OSError, ValueError) as exc:
        typer.echo(f"Не удалось прочитать конфиг {config_path}: {exc}", err=True)
        raise typer.Exit(1) from exc


def _fail(exc: DataError) -> None:
    typer.echo(f"ERROR: {exc}")
    raise typer.Exit(1) from exc


def _table(config: DataConfig, rows: dict[tuple[str, str], int]) -> str:
    splits = list(SourceSplit)
    lines = [f"{'task':<17}" + "".join(f"{s.value:>14}" for s in splits)]
    for task in config.tasks:
        cells = [rows.get((str(task), s.value)) for s in splits]
        lines.append(f"{task.value:<17}" + "".join(f"{('-' if c is None else c):>14}" for c in cells))
    return "\n".join(lines)


def _site_line(config: DataConfig) -> str:
    site = config.site_path
    if site is not None and site.is_dir():
        tasks = sorted(p.name for p in site.iterdir() if p.is_dir() and any(p.glob("*.jsonl")))
        return f"site data: found {site} ({len(tasks)} tasks: {', '.join(tasks)})"
    return f"site data: not found ({site}) — warning: overlap report will cover open data only"


@data_app.command()
def download(
    config_path: ConfigOpt = DEFAULT_CONFIG,
    force: Annotated[bool, typer.Option("--force", help="Re-download even verified files.")] = False,
) -> None:
    """Download and verify open RuMedBench files pinned in the config."""
    from medbench.data.download import download_all

    config = _load(config_path)
    typer.echo(f"RuMedBench {config.source.repo} @ {config.source.commit[:7]} → {config.commit_dir}")
    try:
        report = download_all(config, force=force)
    except DataError as exc:
        _fail(exc)
    typer.echo(_table(config, report.rows))
    typer.echo(f"downloaded: {len(report.downloaded)} · skipped (verified): {len(report.skipped)}")
    typer.echo(_site_line(config))


@data_app.command()
def verify(
    config_path: ConfigOpt = DEFAULT_CONFIG,
    check_sha: Annotated[bool, typer.Option("--check-sha/--no-check-sha", help="Verify sha256.")] = True,
) -> None:
    """Offline check of local files: sha256, rows, schema."""
    from medbench.data.download import verify_all

    config = _load(config_path)
    try:
        report = verify_all(config, check_sha=check_sha)
    except DataError as exc:
        _fail(exc)
    typer.echo(_table(config, report.rows))
    typer.echo(f"OK: {len(report.rows)} files verified")


def _reports_dir(config: DataConfig) -> Path:
    return config.root / "reports" / "data"


@data_app.command()
def overlap(config_path: ConfigOpt = DEFAULT_CONFIG) -> None:
    """Overlap report: site splits × open splits → reports/data/overlap.{md,json}."""
    from medbench.data.overlap import build_overlap_report, write_overlap_report

    config = _load(config_path)
    try:
        report = build_overlap_report(config)
    except DataError as exc:
        _fail(exc)
    if not report.site_found:
        typer.echo(f"warning: site data not found ({config.site_path}); open-only report")
    md, js = write_overlap_report(report, _reports_dir(config))
    for task, rows in report.pairs.items():
        for site_split, cols in rows.items():
            hits = ", ".join(f"{k}={v}" for k, v in cols.items() if v)
            typer.echo(f"{task:<12} {site_split:<11} ∩ {hits or 'none'}")
    typer.echo(f"label conflicts: {len(report.label_conflicts)} · written: {md}, {js}")


@data_app.command()
def stats(config_path: ConfigOpt = DEFAULT_CONFIG) -> None:
    """Dataset statistics → reports/data/stats.{md,json} + length_<task>.png."""
    from medbench.data.stats import build_stats, write_stats

    config = _load(config_path)
    try:
        result = build_stats(config)
    except DataError as exc:
        _fail(exc)
    md, js, pngs = write_stats(result, _reports_dir(config))
    typer.echo(_table(config, {(t, s): v["rows"] for t, d in result.tasks.items() for s, v in d["splits"].items()}))
    typer.echo("paper sizes: " + ("all match" if not result.paper_mismatches else "; ".join(result.paper_mismatches)))
    typer.echo(f"written: {md}, {js}, {len(pngs)} PNG")
