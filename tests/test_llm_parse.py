import pytest

from medbench.llm.parse import parse_answer


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Рассуждение…\nОтвет: entailment", "entailment"),
        ("**Ответ:** **contradiction**", "contradiction"),
        ("Ответ: neutral.", "neutral"),
        ("Отношение: **противоречие** (contradiction).", "contradiction"),
        ("Гипотеза следует из посылки.", "entailment"),
        ("Это нейтральное утверждение.", "neutral"),
        ("Скорее entailment или neutral", None),
        ("Посылка не противоречит… Ответ: entailment", "entailment"),
        ("", None),
        ("Не знаю", None),
    ],
)
def test_nli(text, expected):
    assert parse_answer("RuMedNLI", text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Да.", "да"), ("Ответ: нет", "нет"), ("**Ответ: Да**", "да"), ("да и нет", None), ("Yes", "да"), ("наверное", None)],
)
def test_danet(text, expected):
    assert parse_answer("RuMedDaNet", text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ответ: 2", 2),
        ("Верный вариант 3.", 3),
        ("Ответ: **4**", 4),
        ("Варианты 1 и 2 неверны.\nОтвет: 3", 3),
        ("Ответ: 5", None),
        ("2 или 3", None),
        ("Доза 2,5 мг", None),
    ],
)
def test_rumedtest(text, expected):
    assert parse_answer("RuMedTest", text) == expected
