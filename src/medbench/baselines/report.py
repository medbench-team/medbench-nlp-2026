"""Reproduction report: our final naive/linear runs vs the paper's Naive and TF-IDF (FR-006)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from medbench.data import Role
from medbench.eval import EvalError, list_runs
from medbench.eval.leaderboard import PREVIOUS_ART, load_previous_art
from medbench.eval.metrics import OVERALL_TASKS, TaskMetrics, overall
from medbench.eval.runs import RESULTS_DIR

PAPER_SYSTEM = {"naive": "Naive", "linear": "TF-IDF + LogReg/CRF"}
TOLERANCE = {"naive": 0.01, "linear": 1.0}
EXPLAINED = {("naive", "RuMedNER")}  # ADR-018: official naive NER strategy is not published
REASONS = [
    "ADR-014: из train удалены точные дубликаты test (RuMedNER — 28 строк, RuMedSymptomRec — 1); "
    "официальные модели обучались на сыром train.",
    "ADR-018: код официального Naive не опубликован; для NER используется «самый частый тег токена в train» "
    "(совпадение с официальными предсказаниями ~98% токенов) — сравнение без допуска.",
    "ADR-019: scikit-learn 1.9 — one-vs-rest через OneVsRestClassifier, max_iter=1000 (в статье — старый "
    "LogisticRegression(multi_class='ovr'), max_iter=100); решатели и версии библиотек отличаются.",
]


@dataclass
class Line:
    approach: str
    task: str
    metric: str
    ours: float
    paper: float
    delta: float
    status: str  # ok | out | explained


@dataclass
class ReproductionReport:
    lines: list[Line] = field(default_factory=list)
    overall: dict[str, dict[str, float | None]] = field(default_factory=dict)
    runs: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def in_tolerance(self) -> tuple[int, int]:
        judged = [l for l in self.lines if l.status != "explained"]
        return sum(l.status == "ok" for l in judged), len(judged)


def build_reproduction_report(results_dir: Path | str = RESULTS_DIR, previous_art: Path | str = PREVIOUS_ART) -> ReproductionReport:
    paper = {p.system: p for p in load_previous_art(previous_art)}
    latest: dict[tuple[str, str], object] = {}
    for meta in list_runs(results_dir):
        if meta.role is Role.FINAL and meta.approach in PAPER_SYSTEM and meta.metrics:
            latest[(meta.approach, str(meta.task))] = meta  # sorted by run_id → latest wins
    if not latest:
        raise EvalError("Нет финальных прогонов naive/linear: запустите `uv run medbench baselines run --role final`.")
    report = ReproductionReport()
    for approach, system in PAPER_SYSTEM.items():
        per_task: dict[str, TaskMetrics] = {}
        for task in OVERALL_TASKS:
            meta = latest.get((approach, task))
            if meta is None:
                continue
            report.runs.setdefault(approach, {})[task] = meta.run_id
            per_task[task] = TaskMetrics(**meta.metrics)
            for metric, ours in meta.metrics.items():
                ref = paper[system].metrics[task][metric]
                delta = ours - ref
                status = "explained" if (approach, task) in EXPLAINED else (
                    "ok" if abs(delta) <= TOLERANCE[approach] + 1e-9 else "out")
                report.lines.append(Line(approach, task, metric, ours, ref, delta, status))
        ours_overall = overall(per_task)
        report.overall[approach] = {"ours": ours_overall, "paper": paper[system].overall,
                                    "delta": None if ours_overall is None else ours_overall - paper[system].overall}
        if ours_overall is not None and (approach, "RuMedNER") not in EXPLAINED:
            ok = abs(ours_overall - paper[system].overall) <= TOLERANCE[approach] + 1e-9
            report.lines.append(Line(approach, "Overall", "-", ours_overall, paper[system].overall,
                                     ours_overall - paper[system].overall, "ok" if ok else "out"))
    return report


def render_markdown(report: ReproductionReport) -> str:
    ok, total = report.in_tolerance
    mark = {"ok": "✅", "out": "❌", "explained": "ℹ️"}
    out = [
        "# Воспроизведение бейзлайнов статьи RuMedBench",
        "",
        "Сгенерировано `uv run medbench baselines report` по последним финальным прогонам (открытый test). "
        "Допуск: naive ≤ 0.01 п.п., linear (TF-IDF + LogReg / CRF) ≤ 1 п.п.",
        "",
        f"**В допуске: {ok} из {total}** (ℹ️ — расхождение объяснено, без допуска).",
        "",
        "| Подход | Задача | Метрика | Наше | Статья | Δ | |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in report.lines:
        out.append(f"| {l.approach} | {l.task} | {l.metric} | {l.ours:.2f} | {l.paper:.2f} | {l.delta:+.2f} | {mark[l.status]} |")
    out += ["", "## Overall", ""]
    for approach, o in report.overall.items():
        ours = "—" if o["ours"] is None else f"{o['ours']:.2f}"
        delta = "" if o["delta"] is None else f" (Δ {o['delta']:+.2f})"
        out.append(f"- {approach}: {ours} против {o['paper']:.2f} в статье{delta}")
    out += ["", "## Причины расхождений", "", *[f"- {r}" for r in REASONS], "", "## Прогоны", ""]
    for approach, runs in report.runs.items():
        out += [f"- {approach} / {task}: `{rid}`" for task, rid in runs.items()]
    return "\n".join(out) + "\n"


def write_reproduction_report(report: ReproductionReport, out_dir: Path | str = Path("reports/baselines")) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md, js = out_dir / "reproduction.md", out_dir / "reproduction.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js
