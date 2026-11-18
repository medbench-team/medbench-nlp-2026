"""`medbench eval paper`: reproduce Table 3 of the RuMedBench paper from official predictions (SC-001)."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from medbench.data.download import fetch_url, sha256_file
from medbench.data.errors import ChecksumError
from medbench.eval.metrics import TaskMetrics, overall
from medbench.eval.scoring import metrics_from_pairs

DEFAULT_CONFIG = Path("configs/paper_outputs.yaml")
GOLD_FIELD = {"RuMedTop3": "code", "RuMedSymptomRec": "code", "RuMedDaNet": "answer",
              "RuMedNLI": "gold_label", "RuMedNER": "ner_tags"}


@dataclass
class SetResult:
    name: str
    paper_row: str
    metrics: dict[str, TaskMetrics] = field(default_factory=dict)
    overall: float | None = None
    mismatches: list[str] = field(default_factory=list)


def metrics_from_official_file(task: str, path: Path) -> TaskMetrics:
    """Metrics from a file in the official output format (gold field + `prediction`)."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold = [r[GOLD_FIELD[task]] for r in rows]
    pred = [r["prediction"] for r in rows]
    return metrics_from_pairs(task, gold, pred)


def reproduce_paper(config_path: Path | str = DEFAULT_CONFIG, cache_root: Path = Path("data/paper_outputs")) -> list[SetResult]:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    tol, cache = float(cfg["tolerance"]), cache_root / cfg["commit"]
    results = []
    for s in cfg["sets"]:
        res = SetResult(name=s["name"], paper_row=s["paper_row"])
        for f in s["files"]:
            local = cache / s["name"] / Path(f["path"]).name
            if not (local.is_file() and sha256_file(local) == f["sha256"]):
                fetch_url(f"{cfg['base_url'].rstrip('/')}/{cfg['commit']}/{f['path']}", local)
                if sha256_file(local) != f["sha256"]:
                    actual = sha256_file(local)
                    local.unlink()
                    raise ChecksumError(local, f["sha256"], actual)
            m = metrics_from_official_file(f["task"], local)
            res.metrics[f["task"]] = m
            for k, expected in f["expected"].items():
                got = m.as_dict()[k]
                if abs(got - expected) > tol:
                    res.mismatches.append(f"{f['task']}.{k}: {got:.2f} != {expected:.2f}")
        res.overall = overall(res.metrics)
        if res.overall is None or abs(res.overall - s["overall"]) > tol:
            res.mismatches.append(f"overall: {res.overall} != {s['overall']:.2f}")
        results.append(res)
    return results
