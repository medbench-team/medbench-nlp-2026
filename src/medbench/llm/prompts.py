"""Zero-shot prompts v1 (research.md R6). The answer format is enforced by the prompt (ADR-020)."""

from medbench.data import DaNetExample, Example, NLIExample, TaskName, TestExample

SYSTEM = "Ты — опытный врач-эксперт. Отвечай точно и строго в указанном формате."

FORMAT_LINE = {
    TaskName.NLI: "Ответ: entailment | contradiction | neutral",
    TaskName.DANET: "Ответ: да | нет",
    TaskName.TEST: "Ответ: 1 | 2 | 3 | 4",
}


def _user_nli(e: NLIExample) -> str:
    return (
        "Определи логическое отношение между посылкой (фрагмент медицинской карты) и гипотезой.\n"
        "- entailment — гипотеза следует из посылки;\n"
        "- contradiction — гипотеза противоречит посылке;\n"
        "- neutral — гипотеза может быть как верной, так и неверной.\n\n"
        f"Посылка: {e.premise}\n"
        f"Гипотеза: {e.hypothesis}\n\n"
        "Последняя строка ответа должна иметь вид «Ответ: <метка>», где метка — entailment, "
        "contradiction или neutral."
    )


def _user_danet(e: DaNetExample) -> str:
    return (
        "Прочитай медицинский текст и ответь на вопрос «да» или «нет», опираясь на текст.\n\n"
        f"Текст: {e.context}\n"
        f"Вопрос: {e.question}\n\n"
        "Последняя строка ответа должна иметь вид «Ответ: да» или «Ответ: нет»."
    )


def _user_test(e: TestExample) -> str:
    options = "\n".join(f"{i}. {opt}" for i, opt in enumerate(e.options, start=1))
    return (
        "Это вопрос теста по общей врачебной практике. Ровно один вариант ответа верный.\n\n"
        f"Вопрос: {e.question}\n{options}\n\n"
        "Последняя строка ответа должна иметь вид «Ответ: <номер>», где номер — 1, 2, 3 или 4."
    )


def build_messages(task: TaskName | str, example: Example) -> list[dict[str, str]]:
    task = TaskName(task)
    builders = {TaskName.NLI: _user_nli, TaskName.DANET: _user_danet, TaskName.TEST: _user_test}
    if task not in builders:
        raise ValueError(f"{task}: нет промпта (LLM-потолок — только NLI, DaNet, RuMedTest)")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": builders[task](example)}]


def correction_message(task: TaskName | str) -> dict[str, str]:
    return {
        "role": "user",
        "content": "Не удалось распознать ответ. Ответь заново одной строкой строго в формате "
                   f"«{FORMAT_LINE[TaskName(task)]}» (выбери одно значение).",
    }
