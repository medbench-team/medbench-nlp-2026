import asyncio

import pytest

from medbench.data import get_role
from medbench.llm.cache import LLMResponse, ResponseCache
from medbench.llm.config import LLMConfig
from medbench.llm.graph import build_graph, run_examples
from medbench.llm.provider import LLMCallError

CONFIG = LLMConfig(models=("fake",), fallback={"RuMedNLI": "neutral", "RuMedDaNet": "да", "RuMedTest": 1},
                   format_retries=2, concurrency=4)


class FakeModel:
    """Scripted async model: answers[i] is the reply to the i-th call for an example (by premise)."""

    def __init__(self, script):
        self.script = script
        self.calls = 0
        self.per_example: dict[str, int] = {}

    async def __call__(self, messages):
        self.calls += 1
        user = messages[1]["content"]
        n = self.per_example.get(user, 0)
        self.per_example[user] = n + 1
        reply = self.script(n)
        if isinstance(reply, Exception):
            raise reply
        await asyncio.sleep(0)
        return LLMResponse(content=reply, input_tokens=10, output_tokens=3, latency_s=0.01)


def run(graph, examples):
    return asyncio.run(run_examples(graph, examples, CONFIG.concurrency))


@pytest.fixture
def nli(downloaded_config):
    return get_role("RuMedNLI", "tune", downloaded_config)


def test_valid_first_try(tmp_path, nli):
    model = FakeModel(lambda n: "Ответ: entailment")
    res = run(build_graph("fake", "RuMedNLI", model, ResponseCache(tmp_path / "c.sqlite"), CONFIG), nli)
    assert all(r.label == "entailment" and not r.invalid and r.attempts == 1 for r in res)
    assert model.calls == len(nli)
    assert res[0].usage["requests"] == 1 and res[0].usage["input_tokens"] == 10


def test_retry_then_valid(tmp_path, nli):
    model = FakeModel(lambda n: "не уверен" if n == 0 else "Ответ: contradiction")
    res = run(build_graph("fake", "RuMedNLI", model, ResponseCache(tmp_path / "c.sqlite"), CONFIG), nli)
    assert all(r.label == "contradiction" and r.attempts == 2 and not r.invalid for r in res)


def test_fallback_after_retries(tmp_path, nli):
    model = FakeModel(lambda n: "не знаю")
    res = run(build_graph("fake", "RuMedNLI", model, ResponseCache(tmp_path / "c.sqlite"), CONFIG), nli)
    assert all(r.invalid and r.label == "neutral" and r.attempts == 1 + CONFIG.format_retries for r in res)
    assert res[0].raw == "не знаю"


def test_call_error_goes_to_fallback(tmp_path, nli):
    model = FakeModel(lambda n: LLMCallError("boom"))
    res = run(build_graph("fake", "RuMedNLI", model, ResponseCache(tmp_path / "c.sqlite"), CONFIG), nli)
    assert all(r.invalid and r.label == "neutral" for r in res)


def test_second_run_uses_cache(tmp_path, nli):
    cache = ResponseCache(tmp_path / "c.sqlite")
    first = FakeModel(lambda n: "не уверен" if n == 0 else "Ответ: entailment")
    run(build_graph("fake", "RuMedNLI", first, cache, CONFIG), nli)
    second = FakeModel(lambda n: "Ответ: neutral")
    res = run(build_graph("fake", "RuMedNLI", second, cache, CONFIG), nli)
    assert second.calls == 0
    assert all(r.label == "entailment" and r.usage["cache_hits"] == 2 and r.usage["requests"] == 0 for r in res)


def test_many_examples_concurrently(tmp_path, nli):
    examples = [e.model_copy(update={"id": f"x{i}", "premise": f"{e.premise} {i}"}) for i, e in enumerate(nli * 5)]
    model = FakeModel(lambda n: "Ответ: neutral")
    res = run(build_graph("fake", "RuMedNLI", model, ResponseCache(tmp_path / "c.sqlite"), CONFIG), examples)
    assert [r.id for r in res] == [e.id for e in examples]
    assert model.calls == len(examples)
