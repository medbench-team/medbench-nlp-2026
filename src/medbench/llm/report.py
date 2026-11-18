"""Ceiling report: zero-shot LLMs on the tune role vs baselines and previous art (FR-006)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from medbench.data import Role
from medbench.eval import EvalError, list_runs
from medbench.eval.leaderboard import PREVIOUS_ART, load_previous_art
from medbench.eval.runs import RESULTS_DIR
from medbench.llm.runner import APPROACH

TASKS = ("RuMedNLI", "RuMedDaNet")
BASELINES = ("naive", "linear")


@dataclass
class Cell:
    acc: float
    invalid_rate: float | None = None
    in_per_ex: float | None = None
    out_per_ex: float | None = None
    latency_s: float | None = None
    run_id: str | None = None


@dataclass
class CeilingReport:
    models: dict[str, dict[str, Cell]] = field(default_factory=dict)
    baselines: dict[str, dict[str, Cell]] = field(default_factory=dict)
    previous_art: dict[str, tuple[str, float]] = field(default_factory=dict)  # task → (system, acc)
    best: dict[str, tuple[str, float]] = field(default_factory=dict)
    verdict: dict[str, str] = field(default_factory=dict)


def build_ceiling_report(results_dir: Path | str = RESULTS_DIR, previous_art: Path | str = PREVIOUS_ART) -> CeilingReport:
    rep = CeilingReport()
    for m in list_runs(results_dir):  # sorted by time → latest wins
        if m.role is not Role.TUNE or str(m.task) not in TASKS or not m.metrics:
            continue
        if m.approach == APPROACH:
            u = m.usage or {}
            n = max(1, m.n_examples)
            rep.models.setdefault(m.model, {})[str(m.task)] = Cell(
                m.metrics["acc"], m.invalid_rate, u.get("input_tokens", 0) / n, u.get("output_tokens", 0) / n,
                u.get("latency_s_mean"), m.run_id)
        elif m.approach in BASELINES:
            rep.baselines.setdefault(m.approach, {})[str(m.task)] = Cell(m.metrics["acc"], run_id=m.run_id)
    if not rep.models:
        raise EvalError("Нет tune-прогонов LLM: запустите `uv run medbench llm run`.")
    for p in load_previous_art(previous_art):
        if p.test != "open" or p.human:
            continue
        for t in TASKS:
            acc = p.metrics.get(t, {}).get("acc")
            if acc is not None and acc > rep.previous_art.get(t, ("", -1.0))[1]:
                rep.previous_art[t] = (p.system, acc)
    for t in TASKS:
        cands = [(name, cells[t].acc) for name, cells in rep.models.items() if t in cells]
        if not cands:
            continue
        name, acc = max(cands, key=lambda x: x[1])
        rep.best[t] = (name, acc)
        linear = rep.baselines.get("linear", {}).get(t)
        prev = rep.previous_art.get(t)
        if prev and acc >= prev[1]:
            rep.verdict[t] = (f"LLM: zero-shot {name} уже на уровне/выше previous art на dev ({acc:.2f} ≥ {prev[1]:.2f}) — "
                              "кандидат на финал; дальше — промпты (005)")
        elif linear and acc - linear.acc >= 10:
            rep.verdict[t] = (f"LLM перспективна: +{acc - linear.acc:.1f} п.п. к TF-IDF, но ниже previous art "
                              f"({prev[1]:.2f}) — нужны few-shot/CoT (005) и сравнение с энкодерами (006)")
        else:
            rep.verdict[t] = "Энкодер: zero-shot LLM не даёт заметного выигрыша — приоритет дообучения (006)"
    return rep


def render_markdown(rep: CeilingReport) -> str:
    out = ["# Потолок LLM (zero-shot, роль tune — открытый dev)", "",
           "Сгенерировано `uv run medbench llm report`. Acc в %, invalid — доля нераспознанных ответов "
           "(резервная метка), токены — среднее на пример (вход / выход, включая рассуждение), задержка — "
           "среднее на запрос.", "",
           "| Модель | " + " | ".join(f"{t} Acc | invalid | ток. in/out | сек" for t in TASKS) + " |",
           "|---|" + "---|---|---|---|" * len(TASKS)]
    for model, cells in sorted(rep.models.items()):
        row = []
        for t in TASKS:
            c = cells.get(t)
            if c is None:
                row += ["—"] * 4
                continue
            best = rep.best.get(t, ("", 0))[0] == model
            acc = f"**{c.acc:.2f}**" if best else f"{c.acc:.2f}"
            row += [acc, f"{100 * (c.invalid_rate or 0):.1f}%", f"{c.in_per_ex:.0f} / {c.out_per_ex:.0f}",
                    f"{c.latency_s:.1f}" if c.latency_s is not None else "—"]
        out.append(f"| {model} | " + " | ".join(row) + " |")
    for name, cells in rep.baselines.items():
        out.append(f"| {name} (бейзлайн) | " + " | ".join(
            (f"{cells[t].acc:.2f} | — | — | —" if t in cells else "— | — | — | —") for t in TASKS) + " |")
    out += ["", "Ориентир previous art (открытый **test**, не dev): " + ", ".join(
        f"{t} {acc:.2f} ({system})" for t, (system, acc) in rep.previous_art.items()), "", "## Выводы", ""]
    out += [f"- **{t}**: лучшая — {rep.best[t][0]} ({rep.best[t][1]:.2f}). {rep.verdict[t]}" for t in rep.best]
    return "\n".join(out) + "\n"


def write_ceiling_report(rep: CeilingReport, out_dir: Path | str = Path("reports/llm")) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md, js = out_dir / "ceiling.md", out_dir / "ceiling.json"
    md.write_text(render_markdown(rep), encoding="utf-8")
    js.write_text(json.dumps(asdict(rep), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js
