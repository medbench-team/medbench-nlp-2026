"""Fit once on `train`, predict requested roles, store via medbench.eval.save_run (data-model.md)."""

from dataclasses import dataclass
from pathlib import Path

from medbench.baselines.linear import LinearBaseline
from medbench.baselines.naive import NaiveBaseline
from medbench.data import DataConfig, Role, RoleUnavailableError, TaskName, get_role
from medbench.data.roles import ROLE_TABLE
from medbench.eval import FinalRunExistsError, save_run
from medbench.eval.runs import RESULTS_DIR

APPROACHES = {"naive": NaiveBaseline, "linear": LinearBaseline}


@dataclass
class RunOutcome:
    approach: str
    task: str
    role: str
    status: str  # saved | skipped
    run_id: str | None = None
    metrics: dict[str, float] | None = None
    reason: str | None = None

    def __str__(self) -> str:
        head = f"{self.approach:<7} {self.task:<16} {self.role:<7}"
        if self.status == "skipped":
            return f"{head} skip: {self.reason}"
        metrics = " / ".join(f"{k}={v:.2f}" for k, v in (self.metrics or {}).items()) or "no local metrics"
        return f"{head} → {metrics} | saved {self.run_id}"


def run_baselines(
    approaches: list[str],
    tasks: list[TaskName | str],
    roles: list[Role | str],
    justification: str | None = None,
    config: DataConfig | None = None,
    results_dir: Path | str = RESULTS_DIR,
    on_outcome=None,
) -> list[RunOutcome]:
    outcomes: list[RunOutcome] = []

    def emit(outcome: RunOutcome) -> None:
        outcomes.append(outcome)
        if on_outcome:
            on_outcome(outcome)

    roles = [Role(r) for r in roles]
    for name in approaches:
        for task in (TaskName(t) for t in tasks):
            baseline = APPROACHES[name]()
            if not baseline.supports(task):
                for role in roles:
                    emit(RunOutcome(name, task, role, "skipped", reason=f"{name} не поддерживает {task} (нет train)"))
                continue
            available = [r for r in roles if r in ROLE_TABLE[task]]
            for role in roles:
                if role not in available:
                    emit(RunOutcome(name, task, role, "skipped", reason=f"роль {role} недоступна для {task}"))
            if not available:
                continue
            try:
                train = get_role(task, Role.TRAIN, config)
            except RoleUnavailableError:
                train = []  # RuMedTest: naive needs no training data
            baseline.fit(task, train)
            for role in available:
                preds = baseline.predict(task, get_role(task, role, config))
                try:
                    run = save_run(task, role, preds, approach=name, model="-", params=baseline.params,
                                   justification=justification if role is Role.FINAL else None,
                                   config=config, results_dir=results_dir)
                except FinalRunExistsError:
                    emit(RunOutcome(name, task, role, "skipped",
                                    reason="финальный прогон уже есть — повтор только с --justification"))
                    continue
                emit(RunOutcome(name, task, role, "saved", run.meta.run_id, run.meta.metrics))
    return outcomes
