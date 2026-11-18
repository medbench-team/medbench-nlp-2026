"""Unified, immutable example models for all RuMedBench text tasks (data-model.md)."""

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class TaskName(StrEnum):
    NLI = "RuMedNLI"
    DANET = "RuMedDaNet"
    TEST = "RuMedTest"
    NER = "RuMedNER"
    TOP3 = "RuMedTop3"
    SYMPTOM_REC = "RuMedSymptomRec"


class SourceSplit(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"
    PRIVATE_TEST = "private_test"


class Role(StrEnum):
    TRAIN = "train"
    TUNE = "tune"
    FINAL = "final"
    SUBMIT = "submit"


NER_ENTITY_TYPES = ("ADR", "DI", "Drugclass", "Drugform", "Drugname", "Finding")
NER_TAGS = frozenset({"O"} | {f"{p}-{t}" for p in ("B", "I") for t in NER_ENTITY_TYPES})

NonEmptyStr = Annotated[str, Field(min_length=1)]


def _check_not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    return value


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyStr
    split: SourceSplit


class NLIExample(_Base):
    task: Literal[TaskName.NLI] = TaskName.NLI
    premise: NonEmptyStr
    hypothesis: NonEmptyStr
    label: Literal["entailment", "contradiction", "neutral"] | None = None

    _blank = field_validator("premise", "hypothesis")(_check_not_blank)


class DaNetExample(_Base):
    task: Literal[TaskName.DANET] = TaskName.DANET
    context: NonEmptyStr
    question: NonEmptyStr
    label: Literal["да", "нет"] | None = None

    _blank = field_validator("context", "question")(_check_not_blank)


class TestExample(_Base):
    __test__ = False  # not a pytest test class

    task: Literal[TaskName.TEST] = TaskName.TEST
    question: NonEmptyStr
    options: tuple[NonEmptyStr, NonEmptyStr, NonEmptyStr, NonEmptyStr]
    label: Literal[1, 2, 3, 4] | None = None

    _blank = field_validator("question")(_check_not_blank)


class NERExample(_Base):
    task: Literal[TaskName.NER] = TaskName.NER
    tokens: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tags: tuple[str, ...]

    @model_validator(mode="after")
    def _tags_match_tokens(self) -> "NERExample":
        if len(self.tags) != len(self.tokens):
            raise ValueError(f"len(tags)={len(self.tags)} != len(tokens)={len(self.tokens)}")
        unknown = sorted(set(self.tags) - NER_TAGS)
        if unknown:
            raise ValueError(f"unknown NER tags: {unknown}")
        return self


class ClassifExample(_Base):
    task: Literal[TaskName.TOP3, TaskName.SYMPTOM_REC]
    text: NonEmptyStr
    label: NonEmptyStr | None = None

    _blank = field_validator("text")(_check_not_blank)


Example = Annotated[
    Union[NLIExample, DaNetExample, TestExample, NERExample, ClassifExample],
    Field(discriminator="task"),
]
_EXAMPLE_ADAPTER: TypeAdapter[Example] = TypeAdapter(Example)


def raw_to_fields(task: TaskName, row: dict[str, Any]) -> dict[str, Any]:
    """Map source JSONL field names (research.md R4) to unified model fields."""
    task = TaskName(task)
    if task is TaskName.NLI:
        return {"id": row["pairID"], "premise": row["ru_sentence1"], "hypothesis": row["ru_sentence2"],
                "label": row.get("gold_label")}
    if task is TaskName.DANET:
        return {"id": row["pairID"], "context": row["context"], "question": row["question"],
                "label": row.get("answer")}
    if task is TaskName.TEST:
        answer = row.get("answer")
        return {"id": row["idx"], "question": row["question"],
                "options": tuple(row[str(i)] for i in range(1, 5)),
                "label": int(answer) if answer is not None else None}
    if task is TaskName.NER:
        return {"id": row["idx"], "tokens": tuple(row["tokens"]), "tags": tuple(row["ner_tags"])}
    return {"id": row["idx"], "text": row["symptoms"], "label": row.get("code")}


def parse_raw(task: TaskName | str, split: SourceSplit | str, row: dict[str, Any]) -> Example:
    """Validate one source row into a unified Example.

    Raises KeyError for a missing source field and pydantic.ValidationError for invalid values.
    """
    fields = raw_to_fields(TaskName(task), row)
    fields["task"] = TaskName(task)
    fields["split"] = SourceSplit(split)
    return _EXAMPLE_ADAPTER.validate_python(fields)
