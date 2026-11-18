"""Per-example LangGraph: build_prompt → cache_lookup → call_llm → parse → validate → reprompt / fallback.

See data-model.md (ExampleState) and the Klyaksa canvas «004 LLM ceiling».
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from medbench.data import Example, TaskName
from medbench.llm.cache import LLMResponse, ResponseCache, cache_key
from medbench.llm.config import LLMConfig
from medbench.llm.parse import parse_answer
from medbench.llm.prompts import build_messages, correction_message
from medbench.llm.provider import LLMCallError

CallFn = Callable[[list[dict[str, str]]], Awaitable[LLMResponse]]


class ExampleState(TypedDict, total=False):
    example: Example
    messages: list[dict[str, str]]
    key: str
    response: LLMResponse | None
    from_cache: bool
    label: Any
    attempts: int
    invalid: bool
    error: str | None
    usage: dict[str, float]


@dataclass
class ExampleResult:
    id: str
    label: Any
    invalid: bool
    raw: str | None
    attempts: int
    usage: dict[str, float]
    error: str | None = None


def _zero_usage() -> dict[str, float]:
    return {"input_tokens": 0, "output_tokens": 0, "latency_s": 0.0, "requests": 0, "cache_hits": 0}


def build_graph(model: str, task: TaskName | str, call_fn: CallFn, cache: ResponseCache, config: LLMConfig):
    task = TaskName(task)
    generation = config.generation.model_dump()

    def build_prompt(state: ExampleState) -> ExampleState:
        return {"messages": build_messages(task, state["example"]), "attempts": 0, "invalid": False,
                "error": None, "usage": _zero_usage()}

    def cache_lookup(state: ExampleState) -> ExampleState:
        key = cache_key(model, state["messages"], generation, config.prompt_version)
        hit = cache.get(key)
        return {"key": key, "response": hit, "from_cache": hit is not None}

    async def call_llm(state: ExampleState) -> ExampleState:
        try:
            response = await call_fn(state["messages"])
        except LLMCallError as exc:
            return {"response": None, "error": str(exc), "attempts": state["attempts"] + 1}
        cache.put(state["key"], model, response)
        return {"response": response, "error": None}

    def parse(state: ExampleState) -> ExampleState:
        response = state.get("response")
        usage = dict(state["usage"])
        if response is not None:
            usage["input_tokens"] += response.input_tokens
            usage["output_tokens"] += response.output_tokens
            usage["latency_s"] += response.latency_s
            usage["cache_hits" if state.get("from_cache") else "requests"] += 1
        label = parse_answer(task, response.content) if response is not None else None
        return {"label": label, "attempts": state["attempts"] + 1, "usage": usage}

    def reprompt(state: ExampleState) -> ExampleState:
        content = state["response"].content if state.get("response") else ""
        return {"messages": [*state["messages"], {"role": "assistant", "content": content}, correction_message(task)]}

    def fallback(state: ExampleState) -> ExampleState:
        return {"label": config.fallback[task], "invalid": True}

    def after_lookup(state: ExampleState) -> str:
        return "parse" if state["from_cache"] else "call_llm"

    def after_call(state: ExampleState) -> str:
        return "fallback" if state.get("response") is None else "parse"

    def after_parse(state: ExampleState) -> str:
        if state["label"] is not None:
            return END
        return "reprompt" if state["attempts"] <= config.format_retries else "fallback"

    g = StateGraph(ExampleState)
    for name, fn in (("build_prompt", build_prompt), ("cache_lookup", cache_lookup), ("call_llm", call_llm),
                     ("parse", parse), ("reprompt", reprompt), ("fallback", fallback)):
        g.add_node(name, fn)
    g.add_edge(START, "build_prompt")
    g.add_edge("build_prompt", "cache_lookup")
    g.add_conditional_edges("cache_lookup", after_lookup, ["parse", "call_llm"])
    g.add_conditional_edges("call_llm", after_call, ["parse", "fallback"])
    g.add_conditional_edges("parse", after_parse, ["reprompt", "fallback", END])
    g.add_edge("reprompt", "cache_lookup")
    g.add_edge("fallback", END)
    return g.compile()


async def run_examples(graph, examples: list[Example], concurrency: int) -> list[ExampleResult]:
    states = await graph.abatch([{"example": e} for e in examples], config={"max_concurrency": concurrency})
    out = []
    for e, s in zip(examples, states, strict=True):
        raw = s["response"].content[:500] if (s.get("invalid") and s.get("response")) else (s.get("error") or None)
        out.append(ExampleResult(id=e.id, label=s["label"], invalid=bool(s.get("invalid")),
                                 raw=raw[:500] if (raw and s.get("invalid")) else None,
                                 attempts=s["attempts"], usage=s["usage"],
                                 error=s.get("error") if s.get("response") is None else None))
    return out
