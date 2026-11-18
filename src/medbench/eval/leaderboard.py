"""Leaderboard: our runs vs previous art (FR-007, FR-008, ADR-016)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from medbench.data import Role, TaskName
from medbench.eval.metrics import OVERALL_TASKS, TaskMetrics, overall
from medbench.eval.runs import RESULTS_DIR, RunMeta, list_runs

PREVIOUS_ART = Path("configs/previous_art.yaml")
ALLOWED = {
    TaskName.NLI: {"acc"}, TaskName.DANET: {"acc"}, TaskName.TEST: {"acc"},
    TaskName.TOP3: {"acc", "hit3"}, TaskName.SYMPTOM_REC: {"acc", "hit3"}, TaskName.NER: {"acc", "f1"},
}


class PreviousArt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str
    source: str
    test: Literal["open", "site"]
    human: bool = False
    metrics: dict[TaskName, dict[str, float]]
    overall: float | None = None

    @model_validator(mode="after")
    def _metric_names(self) -> "PreviousArt":
        for task, m in self.metrics.items():
            if not m or not set(m) <= ALLOWED[task]:
                raise ValueError(f"{self.system}: метрики {sorted(m)} недопустимы для {task}")
        return self


def load_previous_art(path: Path | str = PREVIOUS_ART) -> list[PreviousArt]:
    return [PreviousArt.model_validate(x) for x in yaml.safe_load(Path(path).read_text(encoding="utf-8"))]


def _tm(m: dict[str, float]) -> TaskMetrics:
    return TaskMetrics(acc=m["acc"], hit3=m.get("hit3"), f1=m.get("f1"))


@dataclass
class Row:
    system: str
    metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    overall: float | None = None
    runs: dict[str, str] = field(default_factory=dict)  # task → run_id
    justifications: dict[str, str] = field(default_factory=dict)
    source: str | None = None
    ours: bool = True


@dataclass
class Leaderboard:
    final: list[Row]
    tune: list[Row]
    previous_open: list[Row]
    site: list[Row]
    best_previous: dict[str, float]  # task → best previous-art score (open, non-human)


def _our_rows(runs: list[RunMeta], role: Role) -> list[Row]:
    rows: dict[tuple, Row] = {}
    for m in sorted((r for r in runs if r.role is role and r.metrics), key=lambda r: r.run_id):
        key = (m.approach, m.model, m.config_hash)
        row = rows.setdefault(key, Row(system=f"{m.approach} · {m.model} · {m.config_hash[:8]}"))
        row.metrics[m.task] = m.metrics  # latest run wins (sorted by run_id = time)
        row.runs[m.task] = m.run_id
        if m.justification:
            row.justifications[m.task] = m.justification
    for row in rows.values():
        row.overall = overall({t: _tm(v) for t, v in row.metrics.items()})
    return list(rows.values())


def build_leaderboard(results_dir: Path | str = RESULTS_DIR, previous_art: Path | str = PREVIOUS_ART) -> Leaderboard:
    runs = list_runs(results_dir)
    prev = load_previous_art(previous_art)
    prev_open = [Row(system=p.system, metrics={str(t): v for t, v in p.metrics.items()}, overall=p.overall,
                     source=p.source, ours=False) for p in prev if p.test == "open"]
    site = [Row(system=p.system, metrics={str(t): v for t, v in p.metrics.items()}, overall=p.overall,
                source=p.source, ours=False) for p in prev if p.test == "site"]
    best = {}
    for t in OVERALL_TASKS:
        scores = [_tm(p.metrics[t]).score for p in prev if p.test == "open" and not p.human and t in p.metrics]
        if scores:
            best[t] = max(scores)
    return Leaderboard(final=_our_rows(runs, Role.FINAL), tune=_our_rows(runs, Role.TUNE),
                       previous_open=prev_open, site=site, best_previous=best)


def _cell(m: dict[str, float] | None, bold: bool = False, delta: float | None = None) -> str:
    if not m:
        return "—"
    text = " / ".join(f"{v:.2f}" for v in m.values())
    if bold:
        text = f"**{text}**"
    if delta is not None:
        text += f" ({delta:+.2f}{' ★' if delta > 0 else ''})"
    return text


def _table(rows: list[Row], best_prev: dict[str, float], with_delta: bool) -> list[str]:
    header = ["Система", *OVERALL_TASKS, "Overall"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    best_score = {t: max((_tm(r.metrics[t]).score for r in rows if t in r.metrics), default=None) for t in OVERALL_TASKS}
    best_overall = max((r.overall for r in rows if r.overall is not None), default=None)
    for r in rows:
        cells = []
        for t in OVERALL_TASKS:
            m = r.metrics.get(t)
            score = _tm(m).score if m else None
            delta = score - best_prev[t] if (with_delta and r.ours and m and t in best_prev) else None
            mark = "†" if t in r.justifications else ""
            cells.append(_cell(m, bold=score is not None and score == best_score[t], delta=delta) + mark)
        ov = "—" if r.overall is None else (f"**{r.overall:.2f}**" if r.overall == best_overall else f"{r.overall:.2f}")
        lines.append(f"| {r.system} | " + " | ".join(cells) + f" | {ov} |")
    return lines


def render_markdown(lb: Leaderboard) -> str:
    out = [
        "# Сводная таблица RuMedBench",
        "",
        "Сгенерировано `uv run medbench eval leaderboard`. Метрики в %: Top3/SymptomRec — Acc / Hit@3, "
        "NER — Acc / F1 (micro по сущностям), остальные — Acc. Overall — среднее 5 задач (две метрики "
        "задачи сначала усредняются), только при наличии всех пяти.",
        "",
        "## Финальные прогоны (открытый test) против previous art",
        "",
        "В скобках — разница с лучшим опубликованным результатом (open test, без человека) по среднему "
        "метрик задачи; ★ — SotA. † — повторный final с обоснованием.",
        "",
    ]
    out += _table(lb.final + lb.previous_open, lb.best_previous, with_delta=True)
    just = [f"- {r.system} / {t}: {j}" for r in lb.final for t, j in r.justifications.items()]
    if just:
        out += ["", "Обоснования повторных final-прогонов:", "", *just]
    out += ["", "## Разработка (роль tune, открытый dev)", ""]
    out += _table(lb.tune, lb.best_previous, with_delta=False) if lb.tune else ["Прогонов пока нет."]
    out += ["", "## Закрытый test сайта medbench.ru", "",
            "Сравнивать только с нашими сабмитами на сайт (ADR-016).", "",
            "| Система | RuMedDaNet | RuMedNLI | RuMedTest | Источник |", "|---|---|---|---|---|"]
    for r in lb.site:
        cells = [_cell(r.metrics.get(t)) for t in ("RuMedDaNet", "RuMedNLI", "RuMedTest")]
        out.append(f"| {r.system} | " + " | ".join(cells) + f" | {r.source} |")
    out += ["", "## Источники previous art", ""]
    out += [f"- {r.system}: {r.source}" for r in lb.previous_open]
    return "\n".join(out) + "\n"


def write_leaderboard(lb: Leaderboard, results_dir: Path | str = RESULTS_DIR) -> tuple[Path, Path]:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    md, js = results_dir / "leaderboard.md", results_dir / "leaderboard.json"
    md.write_text(render_markdown(lb), encoding="utf-8")
    js.write_text(json.dumps(asdict(lb), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js
