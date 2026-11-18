"""`medbench baselines …` commands (contracts/baselines-cli.md)."""

import time
from enum import StrEnum
from typing import Annotated

import typer

from medbench.data import DataError, Role, TaskName
from medbench.eval import EvalError

baselines_app = typer.Typer(help="Baselines: naive and TF-IDF/CRF (paper reproduction).", no_args_is_help=True)


class ApproachChoice(StrEnum):
    NAIVE = "naive"
    LINEAR = "linear"
    ALL = "all"


@baselines_app.command()
def run(
    approach: Annotated[ApproachChoice, typer.Option("--approach")] = ApproachChoice.ALL,
    task: Annotated[list[TaskName] | None, typer.Option("--task", help="Repeatable; default — all tasks.")] = None,
    role: Annotated[list[Role] | None, typer.Option("--role", help="tune (default) | final | submit; repeatable.")] = None,
    justification: Annotated[str | None, typer.Option("--justification", help="For a repeated final run.")] = None,
) -> None:
    """Fit on `train` once and save runs for the requested roles."""
    from medbench.baselines.runner import run_baselines

    approaches = ["naive", "linear"] if approach is ApproachChoice.ALL else [approach.value]
    roles = role or [Role.TUNE]
    if Role.TRAIN in roles:
        typer.echo("ERROR: роль train не сохраняется — используйте tune, final или submit.")
        raise typer.Exit(1)
    start = time.perf_counter()
    try:
        run_baselines(approaches, task or list(TaskName), roles, justification=justification,
                      on_outcome=lambda o: typer.echo(str(o)))
    except (EvalError, DataError) as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(1) from exc
    typer.echo(f"done in {time.perf_counter() - start:.0f}s")


@baselines_app.command()
def report() -> None:
    """Reproduction report: our final runs vs the paper's Naive and TF-IDF → reports/baselines/."""
    from medbench.baselines.report import build_reproduction_report, write_reproduction_report

    try:
        rep = build_reproduction_report()
    except EvalError as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(1) from exc
    for line in rep.lines:
        typer.echo(f"{line.approach:<7} {line.task:<16} {line.metric:<5} ours {line.ours:6.2f}  paper {line.paper:6.2f}"
                   f"  Δ {line.delta:+6.2f}  {line.status}")
    ok, total = rep.in_tolerance
    md, _ = write_reproduction_report(rep)
    typer.echo(f"in tolerance: {ok}/{total} · written: {md}")
