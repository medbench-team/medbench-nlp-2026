"""`medbench llm …` commands (contracts/llm-cli.md)."""

import time
from typing import Annotated

import typer

from medbench.data import DataError, Role, TaskName
from medbench.eval import EvalError

llm_app = typer.Typer(help="LLM ceiling: Ollama Cloud via LangChain + LangGraph.", no_args_is_help=True)


def _fail(exc: Exception) -> None:
    typer.echo(f"ERROR: {exc}")
    raise typer.Exit(1) from exc


@llm_app.command()
def models() -> None:
    """List the Ollama Cloud catalog and check the models from configs/llm_ceiling.yaml."""
    from medbench.llm.config import MissingApiKeyError, load_llm_config
    from medbench.llm.provider import list_cloud_models

    cfg = load_llm_config()
    try:
        catalog = list_cloud_models(cfg)
    except (MissingApiKeyError, OSError) as exc:
        _fail(exc)
    typer.echo(f"catalog: {len(catalog)} models")
    for m in cfg.models:
        typer.echo(f"  {'✓' if m in catalog else '✗ missing'}  {m}")
    if any(m not in catalog for m in cfg.models):
        raise typer.Exit(1)


@llm_app.command()
def run(
    model: Annotated[list[str] | None, typer.Option("--model", help="Repeatable; default — all models in config.")] = None,
    task: Annotated[list[TaskName] | None, typer.Option("--task", help="Repeatable; default — RuMedNLI, RuMedDaNet.")] = None,
    role: Annotated[list[Role] | None, typer.Option("--role", help="tune (default) | final | submit; repeatable.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Smoke test on N examples; nothing is saved.")] = None,
    concurrency: Annotated[int | None, typer.Option("--concurrency", min=1, max=16)] = None,
    justification: Annotated[str | None, typer.Option("--justification", help="For a repeated final run.")] = None,
) -> None:
    """Zero-shot run through the LangGraph pipeline; results are saved via save_run (spec 002)."""
    from medbench.llm.config import MissingApiKeyError, load_llm_config
    from medbench.llm.runner import run_llm

    cfg = load_llm_config()
    if concurrency:
        cfg = cfg.model_copy(update={"concurrency": concurrency})
    start = time.perf_counter()
    try:
        run_llm(model, task, role, limit=limit, justification=justification, config=cfg,
                on_outcome=lambda o: typer.echo(str(o)), progress=typer.echo)
    except (MissingApiKeyError, EvalError, DataError, ValueError, OSError) as exc:
        _fail(exc)
    typer.echo(f"done in {time.perf_counter() - start:.0f}s")


@llm_app.command()
def report() -> None:
    """Ceiling report → reports/llm/ceiling.{md,json}."""
    from medbench.llm.report import build_ceiling_report, write_ceiling_report

    try:
        rep = build_ceiling_report()
    except EvalError as exc:
        _fail(exc)
    md, _ = write_ceiling_report(rep)
    for t, (name, acc) in rep.best.items():
        typer.echo(f"{t}: best {name} {acc:.2f} — {rep.verdict[t]}")
    typer.echo(f"written: {md}")
