"""LangChain ChatOllama for Ollama Cloud + retries on transient errors (research.md R2, R4)."""

import asyncio
import json
import time
import urllib.request

from langchain_ollama import ChatOllama

from medbench.llm.cache import LLMResponse
from medbench.llm.config import LLMConfig, api_key

TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMCallError(RuntimeError):
    """The model could not be reached after all retries (the example is marked invalid)."""


def make_chat(model: str, config: LLMConfig) -> ChatOllama:
    gen = config.generation
    return ChatOllama(
        model=model,
        base_url=config.base_url,
        temperature=gen.temperature,
        reasoning=gen.reasoning,
        num_predict=gen.num_predict,
        client_kwargs={"headers": {"Authorization": f"Bearer {api_key()}"}, "timeout": config.timeout_s},
    )


def _is_transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is not None:
        return int(status) in TRANSIENT_STATUS
    name = type(exc).__name__.lower()
    return any(s in name for s in ("timeout", "connect", "network", "remoteprotocol", "readerror"))


async def call(chat: ChatOllama, messages: list[dict[str, str]], retries: int) -> LLMResponse:
    """One chat completion with exponential backoff (1, 2, 4, 8, 16 s) on transient errors."""
    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            msg = await chat.ainvoke(messages)
        except Exception as exc:  # noqa: BLE001 — classified below
            if attempt < retries and _is_transient(exc):
                await asyncio.sleep(min(2**attempt, 16))
                continue
            raise LLMCallError(f"{type(exc).__name__}: {str(exc)[:200]}") from exc
        usage = msg.usage_metadata or {}
        reasoning = msg.additional_kwargs.get("reasoning_content") or ""
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        return LLMResponse(content=content, reasoning_chars=len(reasoning),
                           input_tokens=int(usage.get("input_tokens", 0)), output_tokens=int(usage.get("output_tokens", 0)),
                           latency_s=time.perf_counter() - start)
    raise LLMCallError("retries exhausted")  # pragma: no cover


def list_cloud_models(config: LLMConfig) -> list[str]:
    req = urllib.request.Request(f"{config.base_url.rstrip('/')}/v1/models",
                                 headers={"Authorization": f"Bearer {api_key()}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return sorted(m["id"] for m in json.load(resp).get("data", []))
