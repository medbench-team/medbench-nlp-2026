import json

from medbench.eval import list_runs
from medbench.llm.cache import LLMResponse
from medbench.llm.config import LLMConfig
from medbench.llm.runner import APPROACH, run_llm


def config(tmp_path):
    return LLMConfig(models=("fake-a",), fallback={"RuMedNLI": "neutral", "RuMedDaNet": "да", "RuMedTest": 1},
                     cache_path=tmp_path / "cache.sqlite")


def factory(answers):
    def make(model):
        async def call(messages):
            return LLMResponse(content=answers, input_tokens=12, output_tokens=4, latency_s=0.02)
        return call
    return make


def run(tmp_path, downloaded_config, **kw):
    params = dict(models=["fake-a"], config=config(tmp_path), data_config=downloaded_config,
                  results_dir=tmp_path / "results", check_catalog=False, call_factory=factory("Ответ: да\nОтвет: neutral"))
    params.update(kw)
    return run_llm(**params)


def test_saved_runs_with_usage(downloaded_config, tmp_path):
    out = run(tmp_path, downloaded_config, call_factory=factory("Ответ: neutral"), tasks=["RuMedNLI"])
    assert [o.status for o in out] == ["saved"]
    meta = list_runs(tmp_path / "results")[0]
    assert meta.approach == APPROACH and meta.model == "fake-a" and meta.role == "tune"
    assert meta.params["prompt_version"] == "v1"
    assert {"input_tokens", "output_tokens", "latency_s_mean", "cache_hits", "requests"} <= set(meta.usage)
    assert meta.invalid_rate == 0


def test_limit_does_not_save(downloaded_config, tmp_path):
    out = run(tmp_path, downloaded_config, call_factory=factory("Ответ: да"), tasks=["RuMedDaNet"], limit=2)
    assert out[0].status == "limited" and out[0].metrics is not None
    assert list_runs(tmp_path / "results") == []


def test_rumedtest_only_submit_and_final_once(downloaded_config, tmp_path):
    out = run(tmp_path, downloaded_config, call_factory=factory("Ответ: 2"), tasks=["RuMedTest"], roles=["tune", "submit"])
    assert [o.status for o in out] == ["skipped", "saved"]
    kw = dict(call_factory=factory("Ответ: да"), tasks=["RuMedDaNet"], roles=["final"])
    assert run(tmp_path, downloaded_config, **kw)[0].status == "saved"
    assert run(tmp_path, downloaded_config, **kw)[0].status == "skipped"


def test_invalid_answers_marked(downloaded_config, tmp_path):
    out = run(tmp_path, downloaded_config, call_factory=factory("не знаю"), tasks=["RuMedNLI"])
    assert out[0].invalid_rate == 1.0
    preds = (tmp_path / "results" / "runs" / out[0].run_id / "preds.jsonl").read_text(encoding="utf-8").splitlines()
    first = json.loads(preds[0])
    assert first["invalid"] is True and first["prediction"] == "neutral" and first["raw"] == "не знаю"


def test_transient_failures_are_retried(downloaded_config, tmp_path):
    from medbench.llm.provider import LLMCallError

    seen: dict[str, int] = {}

    def make(model):
        async def call(messages):
            key = messages[1]["content"]
            seen[key] = seen.get(key, 0) + 1
            if seen[key] == 1:
                raise LLMCallError("ResponseError: 503")
            return LLMResponse(content="Ответ: да", input_tokens=1, output_tokens=1, latency_s=0.01)
        return call

    out = run(tmp_path, downloaded_config, call_factory=make, tasks=["RuMedDaNet"])
    assert out[0].invalid_rate == 0 and out[0].usage["call_errors"] == 0
