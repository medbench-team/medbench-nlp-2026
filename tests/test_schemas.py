import pytest
from pydantic import ValidationError

from medbench.data.errors import DataNotFoundError, SchemaError
from medbench.data.loaders import read_jsonl
from medbench.data.schemas import (
    ClassifExample,
    DaNetExample,
    NERExample,
    NLIExample,
    TaskName,
    TestExample,
)

from .conftest import FIXTURE_FILES

EXPECTED_TYPES = {
    "RuMedNLI": NLIExample,
    "RuMedDaNet": DaNetExample,
    "RuMedTest": TestExample,
    "RuMedNER": NERExample,
    "RuMedTop3": ClassifExample,
    "RuMedSymptomRec": ClassifExample,
}


@pytest.mark.parametrize(
    ("task", "split"), [(t, s) for t, splits in FIXTURE_FILES.items() for s in splits]
)
def test_every_fixture_file_parses(fixtures_dir, task, split):
    examples = read_jsonl(fixtures_dir / "rumedbench" / "data" / task / f"{split}_v1.jsonl", task, split)
    assert examples, "fixture must not be empty"
    for ex in examples:
        assert isinstance(ex, EXPECTED_TYPES[task])
        assert ex.task == TaskName(task)
        assert ex.split == split
        if task == "RuMedNER":
            assert len(ex.tags) == len(ex.tokens)
        elif split == "private_test":
            assert ex.label is None
        else:
            assert ex.label is not None


def test_field_mapping_nli(fixtures_dir):
    ex = read_jsonl(fixtures_dir / "rumedbench/data/RuMedNLI/train_v1.jsonl", "RuMedNLI", "train")[0]
    assert ex.premise and ex.hypothesis and ex.label in {"entailment", "contradiction", "neutral"}


def test_rumedtest_has_four_options(fixtures_dir):
    ex = read_jsonl(fixtures_dir / "rumedbench/data/RuMedTest/private_test_v1.jsonl", "RuMedTest", "private_test")[0]
    assert len(ex.options) == 4


def test_models_are_immutable(fixtures_dir):
    ex = read_jsonl(fixtures_dir / "rumedbench/data/RuMedDaNet/dev_v1.jsonl", "RuMedDaNet", "dev")[0]
    with pytest.raises(ValidationError):
        ex.label = "нет"


@pytest.mark.parametrize(
    ("file", "task", "line", "fragment"),
    [
        ("nli_missing_field.jsonl", "RuMedNLI", 2, "ru_sentence2"),
        ("nli_bad_label.jsonl", "RuMedNLI", 3, "label"),
        ("nli_duplicate_id.jsonl", "RuMedNLI", 2, "дубликат"),
        ("nli_bad_json.jsonl", "RuMedNLI", 2, "JSON"),
        ("ner_length_mismatch.jsonl", "RuMedNER", 1, "len(tags)"),
        ("ner_unknown_tag.jsonl", "RuMedNER", 1, "B-Unknown"),
        ("test_three_options.jsonl", "RuMedTest", 1, "'4'"),
    ],
)
def test_broken_files_report_task_file_and_line(fixtures_dir, file, task, line, fragment):
    path = fixtures_dir / "broken" / file
    with pytest.raises(SchemaError) as info:
        read_jsonl(path, task, "train" if task != "RuMedTest" else "private_test")
    err = info.value
    assert err.line == line
    assert err.task == task
    assert err.file == path
    assert fragment in str(err)
    assert f"строка {line}" in str(err)


def test_missing_file(tmp_path):
    with pytest.raises(DataNotFoundError, match="medbench data download"):
        read_jsonl(tmp_path / "nope.jsonl", "RuMedNLI", "train")
