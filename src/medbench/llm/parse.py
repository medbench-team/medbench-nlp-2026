"""Parse a free-text model answer into a label (research.md R3, ADR-020)."""

import re

from medbench.data import TaskName

_NLI = {
    "entailment": ("entailment", "следует", "следование", "вытекает"),
    "contradiction": ("contradiction", "противоречие", "противоречит"),
    "neutral": ("neutral", "нейтрально", "нейтральное", "нейтральная", "нейтральный", "нейтральн"),
}
_DANET = {"да": ("да", "yes"), "нет": ("нет", "no")}
_ANSWER_LINE = re.compile(r"(?<![\w])(?:ответ|answer)\s*[*_]*\s*[:：]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_WORD = r"(?<![\w-]){}(?![\w-])"


def _clean(text: str) -> str:
    return text.replace("*", " ").replace("_", " ").replace("`", " ").lower()


def _labels_in(task: TaskName, text: str) -> set:
    text = _clean(text)
    if task is TaskName.TEST:
        found = set(re.findall(r"(?<![\d.,])([1-4])(?![\d.,]?\d)", text))
        return {int(x) for x in found}
    table = _NLI if task is TaskName.NLI else _DANET
    hits = set()
    for label, words in table.items():
        for w in words:
            pattern = _WORD.format(re.escape(w)) if w != "нейтральн" else r"(?<![\w-])нейтральн\w*"
            if re.search(pattern, text):
                hits.add(label)
                break
    return hits


def parse_answer(task: TaskName | str, text: str | None) -> str | int | None:
    """Label from an «Ответ: …» line, else the single label mentioned anywhere; None if ambiguous."""
    task = TaskName(task)
    if not text or not text.strip():
        return None
    lines = _ANSWER_LINE.findall(text)
    if lines:
        labels = _labels_in(task, lines[-1])
        if len(labels) == 1:
            return labels.pop()
    labels = _labels_in(task, text)
    return labels.pop() if len(labels) == 1 else None
