"""Overlap report: medbench.ru site splits × open RuMedBench splits (FR-007, ADR-012/013)."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from medbench.data.config import DataConfig
from medbench.data.errors import DataError
from medbench.data.fingerprint import fingerprint
from medbench.data.loaders import load_split, read_jsonl
from medbench.data.schemas import Example, TaskName

SITE_TASKS = (TaskName.NLI, TaskName.DANET, TaskName.TEST)
SITE_SPLITS = ("train", "dev", "test")
# site split → SourceSplit used only for validation metadata (site test has no labels)
_SITE_AS = {"train": "train", "dev": "dev", "test": "private_test"}


@dataclass
class OverlapReport:
    commit: str
    site_found: bool
    sizes: dict[str, dict[str, int]] = field(default_factory=dict)  # task → split name → rows
    pairs: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)  # task → site:x → open:y → n
    open_pairs: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)  # open × open
    label_conflicts: list[dict] = field(default_factory=list)
    in_split_duplicates: dict[str, dict[str, int]] = field(default_factory=dict)
    identical_files: list[tuple[str, str]] = field(default_factory=list)  # (task, site split)


def _index(examples: list[Example]) -> dict[str, Example]:
    return {fingerprint(e): e for e in examples}


def _dups(examples: list[Example]) -> int:
    return sum(n - 1 for n in Counter(fingerprint(e) for e in examples).values() if n > 1)


def _label(e: Example):
    return getattr(e, "label", None) if not hasattr(e, "tags") else e.tags


def _collect_conflicts(report: "OverlapReport", task, name_a, idx_a, name_b, idx_b) -> None:
    for fp in idx_a.keys() & idx_b.keys():
        la, lb = _label(idx_a[fp]), _label(idx_b[fp])
        if la is not None and lb is not None and la != lb:
            report.label_conflicts.append(
                {"task": str(task), "a": name_a, "b": name_b, "id_a": idx_a[fp].id, "id_b": idx_b[fp].id,
                 "label_a": list(la) if isinstance(la, tuple) else la,
                 "label_b": list(lb) if isinstance(lb, tuple) else lb}
            )


def build_overlap_report(config: DataConfig) -> OverlapReport:
    site = config.site_path
    report = OverlapReport(commit=config.source.commit, site_found=bool(site and site.is_dir()))
    for task in config.tasks:
        open_ex = {f"open:{s}": load_split(task, s, config) for s in config.splits(task)}
        open_idx = {name: _index(exs) for name, exs in open_ex.items()}
        report.sizes[task] = {name: len(exs) for name, exs in open_ex.items()}
        report.in_split_duplicates[task] = {name: _dups(exs) for name, exs in open_ex.items()}
        report.open_pairs[task] = {
            a: {b: len(open_idx[a].keys() & open_idx[b].keys()) for b in open_idx if b != a} for a in open_idx
        }
        names = list(open_idx)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                _collect_conflicts(report, task, a, open_idx[a], b, open_idx[b])
        if not report.site_found or task not in SITE_TASKS:
            continue
        report.pairs[task] = {}
        for split in SITE_SPLITS:
            path = site / task / f"{split}.jsonl"
            if not path.is_file():
                continue
            name = f"site:{split}"
            try:
                site_ex = read_jsonl(path, task, _SITE_AS[split])
            except DataError as exc:
                raise DataError(f"Данные сайта не прошли проверку: {exc}") from exc
            report.sizes[task][name] = len(site_ex)
            report.in_split_duplicates[task][name] = _dups(site_ex)
            site_idx = _index(site_ex)
            report.pairs[task][name] = {}
            for open_name, idx in open_idx.items():
                report.pairs[task][name][open_name] = len(site_idx.keys() & idx.keys())
                _collect_conflicts(report, task, name, site_idx, open_name, idx)
            spec = config.file(task, _SITE_AS[split])
            if spec and hashlib.sha256(path.read_bytes()).hexdigest() == spec.sha256:
                report.identical_files.append((str(task), split))
    return report


def _md_table(rows: dict[str, dict[str, int]]) -> list[str]:
    cols = sorted({c for r in rows.values() for c in r}, key=lambda c: ("train", "dev", "test", "private_test").index(c.split(":")[1]))
    out = ["| | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    out += [f"| {r} | " + " | ".join(str(v.get(c, "—")) for c in cols) + " |" for r, v in rows.items()]
    return out


def render_markdown(report: OverlapReport) -> str:
    lines = [
        "# Пересечения данных: сайт medbench.ru × открытый RuMedBench",
        "",
        f"Открытый репозиторий: `sb-ai-lab/MedBench @ {report.commit[:7]}`. "
        "Совпадение — по отпечатку нормализованных входных полей (NFC, нижний регистр, ё→е, пробелы).",
        "Сгенерировано командой `uv run medbench data overlap`.",
        "",
        "## Вывод",
        "",
        "- **dev сайта = открытый test** → подбор моделей и промптов только на открытом dev (ADR-012).",
        "- train сайта ≈ открытые train + dev; test сайта = открытый `private_test` → данные сайта "
        "в роли не входят, используются только для сверки (ADR-013).",
        "- У RuMedTest меток нет ни в одном источнике: качество — только сабмитом на medbench.ru.",
        "",
    ]
    if not report.site_found:
        lines += ["> ⚠️ Папка с данными сайта не найдена — ниже только пересечения внутри открытых данных.", ""]
    for task, rows in report.pairs.items():
        lines += [f"## {task}: сайт × open", "", *_md_table(rows), ""]
    if report.identical_files:
        lines += ["## Побайтово идентичные файлы", ""]
        lines += [f"- {t}: test сайта = open `private_test`" if s == "test" else f"- {t}: site {s}" for t, s in report.identical_files]
        lines.append("")
    lines += ["## Пересечения внутри открытых данных", "",
              "Короткие шаблонные фразы; удаляются из ролей train/tune, test остаётся официальным "
              "(ADR-014, `known_overlaps` в `configs/data.yaml`).", ""]
    for task, rows in report.open_pairs.items():
        bad = {a: {b: n for b, n in r.items() if n} for a, r in rows.items()}
        bad = {a: r for a, r in bad.items() if r}
        lines.append(f"- {task}: " + ("нет" if not bad else json.dumps(bad, ensure_ascii=False)))
    lines += ["", "## Конфликты меток", ""]
    lines += [
        f"- {c['task']}: {c['a']} `{c['id_a']}` = {c['label_a']} vs {c['b']} `{c['id_b']}` = {c['label_b']}"
        for c in report.label_conflicts
    ] or ["Нет."]
    lines += ["", "## Дубликаты внутри сплитов", ""]
    for task, d in report.in_split_duplicates.items():
        nz = {k: v for k, v in d.items() if v}
        lines.append(f"- {task}: " + (", ".join(f"{k}: {v}" for k, v in nz.items()) if nz else "нет"))
    return "\n".join(lines) + "\n"


def write_overlap_report(report: OverlapReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md, js = out_dir / "overlap.md", out_dir / "overlap.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js
