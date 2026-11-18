"""Metrics exactly as in the official RuMedBench `code/eval.py` (research.md R1–R3, ADR-015).

All values are percentages, unrounded. NER F1 is micro-averaged over entities with the same lenient
IOB chunking as seqeval's default `get_entities`; token accuracy is seqeval's `accuracy_score`.
"""

from collections.abc import Sequence
from dataclasses import dataclass

OVERALL_TASKS = ("RuMedTop3", "RuMedSymptomRec", "RuMedDaNet", "RuMedNLI", "RuMedNER")


def accuracy(gold: Sequence, pred: Sequence) -> float:
    if len(gold) != len(pred) or not gold:
        raise ValueError("gold and pred must be non-empty and of equal length")
    return 100.0 * sum(g == p for g, p in zip(gold, pred)) / len(gold)


def hit_at_3(gold: Sequence[str], top3: Sequence[Sequence[str]]) -> float:
    if len(gold) != len(top3) or not gold:
        raise ValueError("gold and top3 must be non-empty and of equal length")
    return 100.0 * sum(g in set(t) for g, t in zip(gold, top3)) / len(gold)


def _split(tag: str) -> tuple[str, str]:
    if tag in ("O", "."):
        return tag, ""
    prefix, _, type_ = tag.partition("-")
    return prefix, type_


def _end_of_chunk(prev_tag: str, tag: str, prev_type: str, type_: str) -> bool:
    return (
        prev_tag in ("E", "S")
        or (prev_tag == "B" and tag in ("B", "S", "O"))
        or (prev_tag == "I" and tag in ("B", "S", "O"))
        or (prev_tag not in ("O", ".") and prev_type != type_)
    )


def _start_of_chunk(prev_tag: str, tag: str, prev_type: str, type_: str) -> bool:
    return (
        tag in ("B", "S")
        or (prev_tag in ("E", "S") and tag in ("E", "I"))
        or (prev_tag == "O" and tag in ("E", "I"))
        or (tag not in ("O", ".") and prev_type != type_)
    )


def ner_entities(tags: Sequence[str]) -> set[tuple[str, int, int]]:
    """Entities (type, begin, end) of one sentence, lenient IOB like seqeval `get_entities`."""
    chunks: set[tuple[str, int, int]] = set()
    prev_tag, prev_type, begin = "O", "", 0
    for i, chunk in enumerate([*tags, "O"]):
        tag, type_ = _split(chunk)
        if _end_of_chunk(prev_tag, tag, prev_type, type_):
            chunks.add((prev_type, begin, i - 1))
        if _start_of_chunk(prev_tag, tag, prev_type, type_):
            begin = i
        prev_tag, prev_type = tag, type_
    return chunks


def ner_token_accuracy(gold: Sequence[Sequence[str]], pred: Sequence[Sequence[str]]) -> float:
    total = correct = 0
    for g, p in zip(gold, pred, strict=True):
        if len(g) != len(p):
            raise ValueError("token sequences must have equal length")
        total += len(g)
        correct += sum(a == b for a, b in zip(g, p))
    return 100.0 * correct / total


def ner_f1(gold: Sequence[Sequence[str]], pred: Sequence[Sequence[str]]) -> float:
    """Micro F1 over entities across all sentences (seqeval `f1_score` default)."""
    tp = n_gold = n_pred = 0
    for g, p in zip(gold, pred, strict=True):
        eg, ep = ner_entities(g), ner_entities(p)
        tp += len(eg & ep)
        n_gold += len(eg)
        n_pred += len(ep)
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    return 100.0 * 2 * precision * recall / (precision + recall) if precision + recall else 0.0


@dataclass(frozen=True)
class TaskMetrics:
    acc: float
    hit3: float | None = None
    f1: float | None = None

    @property
    def score(self) -> float:
        """Task score for Overall: mean of the two metrics, or the single one."""
        second = self.hit3 if self.hit3 is not None else self.f1
        return self.acc if second is None else (self.acc + second) / 2

    def as_dict(self) -> dict[str, float]:
        return {k: v for k, v in (("acc", self.acc), ("hit3", self.hit3), ("f1", self.f1)) if v is not None}

    def __str__(self) -> str:
        return " / ".join(f"{k}={v:.2f}" for k, v in self.as_dict().items())


def overall(per_task: dict[str, TaskMetrics]) -> float | None:
    """Mean over the five paper tasks; None unless all five are present."""
    if not all(t in per_task for t in OVERALL_TASKS):
        return None
    return sum(per_task[t].score for t in OVERALL_TASKS) / len(OVERALL_TASKS)
