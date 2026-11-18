"""`medbench eval …` commands (contracts/eval-api.md)."""

import json
from pathlib import Path
from typing import Annotated

import typer

from medbench.data import DataError, Role, TaskName
from medbench.eval.errors import EvalError

eval_app = typer.Typer(help="Evaluation: metrics, runs, leaderboard, submission.", no_args_is_help=True)

TaskOpt = Annotated[TaskName, typer.Option("--task", help="RuMedBench task.")]
PAPER_TASKS = ("RuMedTop3", "RuMedSymptomRec", "RuMedDaNet", "RuMedNLI", "RuMedNER")


def _fail(exc: Exception) -> None:
    typer.echo(f"ERROR: {exc}")
    raise typer.Exit(1) from exc


@eval_app.command()
def score(
    preds: Annotated[Path, typer.Argument(help="preds.jsonl")],
    task: TaskOpt,
    role: Annotated[Role, typer.Option("--role", help="tune (подбор) или final.")] = Role.TUNE,
) -> None:
    """Validate predictions against a role and print metrics (nothing is saved)."""
    from medbench.eval.predictions import read_predictions
    from medbench.eval.scoring import score as score_fn

    try:
        metrics = score_fn(task, read_predictions(preds), role)
    except (EvalError, DataError, ValueError) as exc:
        _fail(exc)
    typer.echo(f"{task.value} [{role.value}] {metrics}")


@eval_app.command()
def save(
    preds: Annotated[Path, typer.Argument(help="preds.jsonl")],
    task: TaskOpt,
    role: Annotated[Role, typer.Option("--role", help="tune | final | submit")],
    approach: Annotated[str, typer.Option("--approach", help="naive, tfidf, llm-zero-shot, …")],
    model: Annotated[str, typer.Option("--model", help="Model name/tag, '-' for baselines.")] = "-",
    params: Annotated[Path | None, typer.Option("--params", help="JSON file with approach params.")] = None,
    justification: Annotated[str | None, typer.Option("--justification", help="Why a repeated final run.")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Validate, score and store a run in results/runs/<run_id>/."""
    from medbench.eval.predictions import read_predictions
    from medbench.eval.runs import save_run

    try:
        run = save_run(task, role, read_predictions(preds), approach=approach, model=model,
                       params=json.loads(params.read_text(encoding="utf-8")) if params else None,
                       justification=justification, notes=notes)
    except (EvalError, DataError, ValueError) as exc:
        _fail(exc)
    typer.echo(f"saved {run.path}")
    if run.meta.metrics:
        typer.echo(" / ".join(f"{k}={v:.2f}" for k, v in run.meta.metrics.items()))


@eval_app.command()
def rescore(run_dir: Annotated[Path, typer.Argument(help="results/runs/<run_id>")]) -> None:
    """Recompute metrics of a saved run and compare with meta.json."""
    from medbench.eval.runs import rescore as rescore_fn

    try:
        stored, recomputed = rescore_fn(run_dir)
    except (EvalError, DataError) as exc:
        _fail(exc)
    if recomputed is None:
        typer.echo("submit run: no local metrics")
        return
    same = stored is not None and stored.keys() == recomputed.keys() and all(
        abs(stored[k] - recomputed[k]) < 1e-9 for k in stored)
    typer.echo(f"stored:     {stored}\nrecomputed: {recomputed}\n{'OK' if same else 'MISMATCH'}")
    if not same:
        raise typer.Exit(1)


@eval_app.command()
def leaderboard() -> None:
    """Build results/leaderboard.{md,json}: our final/tune runs vs previous art."""
    from medbench.eval.leaderboard import build_leaderboard, write_leaderboard

    lb = build_leaderboard()
    md, js = write_leaderboard(lb)
    typer.echo(f"final systems: {len(lb.final)} · tune systems: {len(lb.tune)} · written: {md}, {js}")


@eval_app.command()
def submit(
    run: Annotated[list[str] | None, typer.Option("--run", help="submit run_id (repeatable); default — latest per task.")] = None,
    naive_fill: Annotated[bool, typer.Option("--naive-fill", help="Fill missing tasks with the naive answer.")] = False,
) -> None:
    """Build a medbench.ru submission zip (RuMedDaNet, RuMedNLI, RuMedTest)."""
    from medbench.eval.submission import build_submission

    try:
        report = build_submission(run_ids=run, naive_fill=naive_fill)
    except (EvalError, DataError) as exc:
        _fail(exc)
    for w in report.warnings:
        typer.echo(f"warning: {w}")
    for task, n in report.rows.items():
        typer.echo(f"{task:<12} {n:>5} rows ← {report.sources[task]}")
    typer.echo(f"written: {report.path}")


@eval_app.command()
def paper() -> None:
    """Reproduce Table 3 of the RuMedBench paper from the official predictions (SC-001)."""
    from medbench.eval.paper import reproduce_paper

    try:
        results = reproduce_paper()
    except (EvalError, DataError) as exc:
        _fail(exc)
    typer.echo(f"{'set':<14}{'paper row':<12}" + "".join(f"{t:>18}" for t in PAPER_TASKS) + f"{'Overall':>9}")
    for r in results:
        cells = "".join(f"{' / '.join(f'{v:.2f}' for v in r.metrics[t].as_dict().values()):>18}" for t in PAPER_TASKS)
        typer.echo(f"{r.name:<14}{r.paper_row:<12}{cells}{r.overall:>9.2f}")
    bad = [f"{r.name}: {m}" for r in results for m in r.mismatches]
    if bad:
        typer.echo("MISMATCH:\n  " + "\n  ".join(bad))
        raise typer.Exit(1)
    typer.echo("OK: all metrics match the paper (≤ 0.01)")
