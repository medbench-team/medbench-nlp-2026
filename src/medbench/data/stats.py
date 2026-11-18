"""Dataset statistics for the report's Dataset section (FR-010, US3)."""

import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from medbench.data.config import DataConfig
from medbench.data.fingerprint import input_fields
from medbench.data.loaders import load_split
from medbench.data.schemas import Example, NERExample, TaskName

# Table 1 of the RuMedBench paper (Blinov et al., 2022); RuMedTest/private_test are not in it.
PAPER_SIZES: dict[str, dict[str, int]] = {
    "RuMedNLI": {"train": 11232, "dev": 1395, "test": 1422},
    "RuMedDaNet": {"train": 1052, "dev": 256, "test": 256},
    "RuMedNER": {"train": 3440, "dev": 676, "test": 693},
    "RuMedTop3": {"train": 4690, "dev": 848, "test": 822},
    "RuMedSymptomRec": {"train": 2470, "dev": 415, "test": 415},
}
TOP_K = 10
TASK_DESCRIPTION = {
    "RuMedNLI": "NLI (entailment / contradiction / neutral), посылка + гипотеза",
    "RuMedDaNet": "бинарный QA (да / нет) по контексту",
    "RuMedTest": "тест по общей врачебной практике, 4 варианта, 1 верный (меток нет)",
    "RuMedNER": "NER, IOB-разметка 6 типов сущностей",
    "RuMedTop3": "классификация жалоб по кодам МКБ-10 (Acc, Hit@3)",
    "RuMedSymptomRec": "рекомендация недостающего симптома (Acc, Hit@3)",
}


@dataclass
class DatasetStats:
    commit: str
    tasks: dict[str, dict] = field(default_factory=dict)
    paper_mismatches: list[str] = field(default_factory=list)


def _words(example: Example) -> int:
    return sum(len(f.split()) for f in input_fields(example))


def _labels(examples: list[Example]) -> Counter:
    if examples and isinstance(examples[0], NERExample):
        return Counter(t[2:] for e in examples for t in e.tags if t.startswith("B-"))
    return Counter(str(e.label) for e in examples if getattr(e, "label", None) is not None)


def _length_summary(lengths: list[int]) -> dict[str, float]:
    ordered = sorted(lengths)
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    return {"min": ordered[0], "median": float(f"{statistics.median(ordered):g}"), "p95": p95, "max": ordered[-1],
            "mean": round(statistics.fmean(ordered), 1)}


def _example_preview(example: Example) -> str:
    fields = input_fields(example)
    text = " ‖ ".join(f[:160] + ("…" if len(f) > 160 else "") for f in fields)
    label = getattr(example, "label", None)
    if isinstance(example, NERExample):
        label = " ".join(example.tags)
    return f"{text} → **{label}**" if label is not None else text


def build_stats(config: DataConfig) -> DatasetStats:
    stats = DatasetStats(commit=config.source.commit)
    for task in config.tasks:
        splits: dict[str, dict] = {}
        examples_for_preview: list[str] = []
        for split in config.splits(task):
            examples = load_split(task, split, config)
            labels = _labels(examples)
            splits[split] = {
                "rows": len(examples),
                "n_classes": len(labels),
                "labels": dict(labels.most_common(TOP_K)),
                "length_words": _length_summary([_words(e) for e in examples]),
                "_lengths": [_words(e) for e in examples],
            }
            if split in ("train", "private_test") and len(examples_for_preview) < 2:
                examples_for_preview.append(_example_preview(examples[0]))
            paper = PAPER_SIZES.get(task, {}).get(split)
            if paper is not None and paper != len(examples):
                stats.paper_mismatches.append(f"{task}/{split}: {len(examples)} vs {paper} в статье")
        stats.tasks[str(task)] = {"description": TASK_DESCRIPTION[task], "splits": splits,
                                  "examples": examples_for_preview}
    return stats


def _render_md(stats: DatasetStats) -> str:
    lines = [
        "# Статистика RuMedBench",
        "",
        f"Открытый репозиторий `sb-ai-lab/MedBench @ {stats.commit[:7]}`. "
        "Сгенерировано командой `uv run medbench data stats`. Длины — в словах (по пробелам) суммарно по "
        "входным полям.",
        "",
        "## Размеры сплитов",
        "",
        "| Задача | train | dev | test | private_test |",
        "|---|---|---|---|---|",
    ]
    for task, t in stats.tasks.items():
        cells = [str(t["splits"].get(s, {}).get("rows", "—")) for s in ("train", "dev", "test", "private_test")]
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    lines += ["", "Сверка со статьёй (таблица 1): "
              + ("все размеры совпадают." if not stats.paper_mismatches else "отличия — " + "; ".join(stats.paper_mismatches)), ""]
    for task, t in stats.tasks.items():
        lines += [f"## {task}", "", t["description"], "",
                  "| Сплит | Примеров | Классов | Длина min / median / p95 / max | Метки (top) |",
                  "|---|---|---|---|---|"]
        for split, s in t["splits"].items():
            ln = s["length_words"]
            labels = ", ".join(f"{k}: {v}" for k, v in s["labels"].items()) or "—"
            lines.append(f"| {split} | {s['rows']} | {s['n_classes'] or '—'} | "
                         f"{ln['min']} / {ln['median']:g} / {ln['p95']} / {ln['max']} | {labels} |")
        lines += ["", f"![Длины {task}](length_{task}.png)", "", "Примеры:", ""]
        lines += [f"- {e}" for e in t["examples"]]
        lines.append("")
    return "\n".join(lines)


def write_stats(stats: DatasetStats, out_dir: Path) -> tuple[Path, Path, list[Path]]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    pngs = []
    for task, t in stats.tasks.items():
        fig, ax = plt.subplots(figsize=(6, 3.5))
        for split, s in t["splits"].items():
            ax.hist(s["_lengths"], bins=40, alpha=0.45, density=True, label=f"{split} (n={s['rows']})")
        ax.set(title=f"{task}: длина входа", xlabel="слов", ylabel="доля примеров")
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = out_dir / f"length_{task}.png"
        fig.savefig(path, dpi=110)
        plt.close(fig)
        pngs.append(path)
    md = out_dir / "stats.md"
    md.write_text(_render_md(stats), encoding="utf-8")
    payload = asdict(stats)
    for t in payload["tasks"].values():
        for s in t["splits"].values():
            s.pop("_lengths", None)
    js = out_dir / "stats.json"
    js.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js, pngs
