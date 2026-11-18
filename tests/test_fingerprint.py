from medbench.data.fingerprint import fingerprint, normalize
from medbench.data.schemas import ClassifExample, NLIExample


def nli(premise: str, hypothesis: str, label="entailment", id_="a") -> NLIExample:
    return NLIExample(id=id_, split="train", premise=premise, hypothesis=hypothesis, label=label)


def test_normalize():
    assert normalize("  Ёлка\tи  ЁЖ\n") == "елка и еж"


def test_same_text_modulo_whitespace_case_yo():
    a = nli("Пациент  стабилен.", "Всё хорошо")
    b = nli("пациент стабилен.", "  все хорошо ", id_="b")
    assert fingerprint(a) == fingerprint(b)


def test_different_text_differs():
    assert fingerprint(nli("Пациент стабилен.", "x")) != fingerprint(nli("Пациент нестабилен.", "x"))


def test_field_boundary_matters():
    assert fingerprint(nli("ab", "c")) != fingerprint(nli("a", "bc"))


def test_label_is_ignored():
    assert fingerprint(nli("p", "h", "entailment")) == fingerprint(nli("p", "h", "neutral"))


def test_task_is_part_of_fingerprint():
    top3 = ClassifExample(id="x", split="train", task="RuMedTop3", text="кашель", label="J06")
    rec = ClassifExample(id="x", split="train", task="RuMedSymptomRec", text="кашель", label="боль")
    assert fingerprint(top3) != fingerprint(rec)
