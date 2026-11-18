"""Models × tasks × roles → LangGraph per example → save_run (spec 002)."""

import asyncio
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from medbench.data import DataConfig, Role, TaskName, get_role
from medbench.data.roles import ROLE_TABLE
from medbench.eval import FinalRunExistsError, Prediction, save_run
from medbench.eval.runs import RESULTS_DIR
from medbench.llm.cache import ResponseCache
from medbench.llm.config import LLMConfig, load_llm_config, run_params
from medbench.llm.graph import ExampleResult, build_graph, run_examples
from medbench.llm.provider import call, list_cloud_models, make_chat

APPROACH = "llm-zero-shot"
LLM_TASKS = (TaskName.NLI, TaskName.DANET, TaskName.TEST)
CHUNK = 50


@dataclass
class LLMOutcome:
    model: str
    task: str
    role: str
    status: str  # saved | skipped | limited
    metrics: dict[str, float] | None = None
    invalid_rate: float | None = None
    usage: dict[str, float] | None = None
    run_id: str | None = None
    reason: str | None = None

    def __str__(self) -> str:
        head = f"{self.model:<22} {self.task:<11} {self.role:<7}"
        if self.status == "skipped":
            return f"{head} skip: {self.reason}"
        m = " / ".join(f"{k}={v:.2f}" for k, v in (self.metrics or {}).items()) or "no local metrics"
        u = self.usage or {}
        n = max(1.0, u.get("examples", 1))
        tail = (f" invalid={100 * (self.invalid_rate or 0):.1f}% tok/ex in={u.get('input_tokens', 0) / n:.0f} "
                f"out={u.get('output_tokens', 0) / n:.0f} lat={u.get('latency_s_mean', 0):.1f}s "
                f"req={u.get('requests', 0):.0f} cache={u.get('cache_hits', 0):.0f}")
        where = f" | saved {self.run_id}" if self.run_id else " | (limit: not saved)"
        return f"{head} → {m}{tail}{where}"


def _aggregate(results: list[ExampleResult]) -> dict[str, float]:
    total = {"input_tokens": 0.0, "output_tokens": 0.0, "requests": 0.0, "cache_hits": 0.0, "latency_s": 0.0}
    for r in results:
        for k in total:
            total[k] += r.usage.get(k, 0)
    calls = total["requests"] + total["cache_hits"]
    return {**{k: v for k, v in total.items() if k != "latency_s"},
            "latency_s_mean": total["latency_s"] / calls if calls else 0.0, "examples": float(len(results))}


async def _run_task(model, task, examples, cfg, cache, call_fn, progress) -> list[ExampleResult]:
    graph = build_graph(model, task, call_fn, cache, cfg)
    results: list[ExampleResult] = []
    for i in range(0, len(examples), CHUNK):  # chunks → progress output and resumability via cache
        results += await run_examples(graph, examples[i:i + CHUNK], cfg.concurrency)
        if progress:
            agg = _aggregate(results)
            progress(f"  {model} {task}: {len(results)}/{len(examples)} cache={agg['cache_hits']:.0f} "
                     f"invalid={sum(r.invalid for r in results)} errors={sum(r.error is not None for r in results)}")
    failed = [i for i, r in enumerate(results) if r.error is not None]
    if failed:  # transient cloud failures: one more pass at half concurrency before marking invalid
        if progress:
            errors = Counter(results[i].error.split(":")[0] for i in failed)
            progress(f"  {model} {task}: retrying {len(failed)} failed calls ({dict(errors)})")
        again = await run_examples(graph, [examples[i] for i in failed], max(1, cfg.concurrency // 2))
        for i, r in zip(failed, again, strict=True):
            results[i] = r
    return results


def run_llm(
    models: list[str] | None = None,
    tasks: list[TaskName | str] | None = None,
    roles: list[Role | str] | None = None,
    limit: int | None = None,
    justification: str | None = None,
    config: LLMConfig | None = None,
    data_config: DataConfig | None = None,
    results_dir: Path | str = RESULTS_DIR,
    call_factory: Callable | None = None,
    check_catalog: bool = True,
    on_outcome: Callable[[LLMOutcome], None] | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[LLMOutcome]:
    cfg = config or load_llm_config()
    models = models or list(cfg.models)
    tasks = [TaskName(t) for t in (tasks or [TaskName.NLI, TaskName.DANET])]
    roles = [Role(r) for r in (roles or [Role.TUNE])]
    if check_catalog:
        available = set(list_cloud_models(cfg))
        missing = [m for m in models if m not in available]
        if missing:
            raise ValueError(f"Модели нет в каталоге Ollama Cloud: {missing}")
    cache = ResponseCache(cfg.cache_path)
    outcomes: list[LLMOutcome] = []

    def emit(o: LLMOutcome) -> None:
        outcomes.append(o)
        if on_outcome:
            on_outcome(o)

    for model in models:
        if call_factory:
            call_fn = call_factory(model)
        else:
            chat = make_chat(model, cfg)
            call_fn = lambda messages, chat=chat: call(chat, messages, cfg.http_retries)  # noqa: E731
        for task in tasks:
            if task not in LLM_TASKS:
                for role in roles:
                    emit(LLMOutcome(model, task, role, "skipped", reason=f"нет промпта для {task}"))
                continue
            for role in roles:
                if role not in ROLE_TABLE[task] or role is Role.TRAIN:
                    emit(LLMOutcome(model, task, role, "skipped", reason=f"роль {role} недоступна для {task}"))
                    continue
                examples = get_role(task, role, data_config)
                if limit:
                    examples = examples[:limit]
                results = asyncio.run(_run_task(model, task, examples, cfg, cache, call_fn, progress))
                preds = [Prediction(id=r.id, prediction=r.label, invalid=r.invalid, raw=r.raw) for r in results]
                usage = _aggregate(results)
                usage["call_errors"] = float(sum(r.error is not None for r in results))
                invalid_rate = sum(p.invalid for p in preds) / len(preds)
                if limit:
                    metrics = None
                    if role is not Role.SUBMIT:
                        gold = {e.id: e.label for e in examples}
                        acc = 100 * sum(gold[p.id] == p.prediction for p in preds) / len(preds)
                        metrics = {"acc": acc}
                    emit(LLMOutcome(model, task, role, "limited", metrics, invalid_rate, usage))
                    continue
                try:
                    run = save_run(task, role, preds, approach=APPROACH, model=model, params=run_params(cfg),
                                   usage={k: v for k, v in usage.items() if k != "examples"},
                                   justification=justification if role is Role.FINAL else None,
                                   config=data_config, results_dir=results_dir)
                except FinalRunExistsError:
                    emit(LLMOutcome(model, task, role, "skipped",
                                    reason="финальный прогон уже есть — повтор только с --justification"))
                    continue
                emit(LLMOutcome(model, task, role, "saved", run.meta.metrics, invalid_rate, usage, run.meta.run_id))
    cache.close()
    return outcomes

