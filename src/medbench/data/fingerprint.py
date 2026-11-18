"""Text normalisation and example fingerprints for overlap/leakage checks (research.md R5)."""

import hashlib
import re
import unicodedata

from medbench.data.schemas import (
    ClassifExample,
    DaNetExample,
    Example,
    NERExample,
    NLIExample,
    TestExample,
)

_WS = re.compile(r"\s+")
_SEP = "␟"  # unit separator between fields


def normalize(text: str) -> str:
    """NFC → lower → ё→е → collapse whitespace → strip."""
    text = unicodedata.normalize("NFC", text).lower().replace("ё", "е")
    return _WS.sub(" ", text).strip()


def input_fields(example: Example) -> tuple[str, ...]:
    """Input fields that identify an example (the label is deliberately excluded)."""
    match example:
        case NLIExample():
            return (example.premise, example.hypothesis)
        case DaNetExample():
            return (example.context, example.question)
        case TestExample():
            return (example.question, *example.options)
        case NERExample():
            return (" ".join(example.tokens),)
        case ClassifExample():
            return (example.text,)
    raise TypeError(f"unsupported example type: {type(example).__name__}")


def fingerprint(example: Example) -> str:
    """SHA-1 of the task name and normalised input fields."""
    payload = _SEP.join((str(example.task), *(normalize(f) for f in input_fields(example))))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
