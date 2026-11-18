"""Root command line interface: `uv run medbench <group> <command>`."""

import typer

from medbench.baselines.commands import baselines_app
from medbench.data.commands import data_app
from medbench.eval.commands import eval_app
from medbench.llm.commands import llm_app

app = typer.Typer(help="MedBench NLP 2026 — RuMedBench tooling.", no_args_is_help=True)
app.add_typer(data_app, name="data")
app.add_typer(eval_app, name="eval")
app.add_typer(baselines_app, name="baselines")
app.add_typer(llm_app, name="llm")


if __name__ == "__main__":
    app()
