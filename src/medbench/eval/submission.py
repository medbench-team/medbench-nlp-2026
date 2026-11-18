"""medbench.ru submission archive in the format of lb_submissions/SAI/Naive/sample_submission.zip (FR-009)."""

import json
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from medbench.data import DataConfig, Role, TaskName, default_config, get_role
from medbench.eval.errors import EvalError
from medbench.eval.predictions import normalize_label, validate_predictions
from medbench.eval.runs import RESULTS_DIR, list_runs, load_run, runs_dir

SUBMIT_TASKS = (TaskName.DANET, TaskName.NLI, TaskName.TEST)
ID_FIELD = {TaskName.DANET: "pairID", TaskName.NLI: "pairID", TaskName.TEST: "idx"}
ANSWER_FIELD = {TaskName.DANET: "answer", TaskName.NLI: "gold_label", TaskName.TEST: "answer"}
NAIVE = {TaskName.DANET: "да", TaskName.NLI: "neutral", TaskName.TEST: 1}  # as in lb_submissions/SAI/Naive


@dataclass
class SubmissionReport:
    path: Path
    sources: dict[str, str] = field(default_factory=dict)  # task → run_id | "naive"
    rows: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _answer(task: TaskName, value) -> str:
    value = normalize_label(task, value)
    return str(value)  # RuMedTest answers are strings "1".."4" in the sample


def build_submission(
    run_ids: list[str] | None = None,
    naive_fill: bool = False,
    results_dir: Path | str = RESULTS_DIR,
    out_dir: Path | str | None = None,
    config: DataConfig | None = None,
) -> SubmissionReport:
    config = config or default_config()
    out_dir = Path(out_dir) if out_dir else Path(results_dir) / "submissions"
    chosen: dict[TaskName, str] = {}
    if run_ids:
        metas = {m.run_id: m for m in list_runs(results_dir)}
        for rid in run_ids:
            meta = metas.get(rid)
            if meta is None:
                raise EvalError(f"Прогон {rid} не найден в {runs_dir(results_dir)}.")
            if meta.role is not Role.SUBMIT or meta.task not in SUBMIT_TASKS:
                raise EvalError(f"{rid}: нужен прогон роли submit для RuMedDaNet/RuMedNLI/RuMedTest.")
            chosen[meta.task] = rid
    else:
        for meta in list_runs(results_dir):  # sorted by time → latest wins
            if meta.role is Role.SUBMIT and meta.task in SUBMIT_TASKS:
                chosen[meta.task] = meta.run_id

    report = SubmissionReport(path=out_dir / f"{datetime.now(UTC):%Y%m%d-%H%M%S}.zip")
    files: dict[str, str] = {}
    for task in SUBMIT_TASKS:
        examples = get_role(task, Role.SUBMIT, config)
        if task in chosen:
            run = load_run(runs_dir(results_dir) / chosen[task], config)
            by_id = validate_predictions(task, Role.SUBMIT, run.predictions, config)
            answers = [_answer(task, by_id[e.id].prediction) for e in examples]
            report.sources[task] = chosen[task]
        elif naive_fill:
            answers = [_answer(task, NAIVE[task])] * len(examples)
            report.sources[task] = "naive"
            report.warnings.append(f"{task}: нет submit-прогона — наивный ответ {NAIVE[task]!r}.")
        else:
            report.warnings.append(f"{task}: нет submit-прогона — файл не включён в архив.")
            continue
        lines = [json.dumps({ID_FIELD[task]: e.id, ANSWER_FIELD[task]: a}, ensure_ascii=False)
                 for e, a in zip(examples, answers, strict=True)]
        assert len({e.id for e in examples}) == len(lines)  # every private_test id exactly once
        files[f"{task}.jsonl"] = "\n".join(lines) + "\n"
        report.rows[task] = len(lines)
    if not files:
        raise EvalError("Нечего отправлять: нет submit-прогонов (используйте --naive-fill для наивного архива).")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(report.path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return report
