"""SQLite cache of model responses (research.md R5). Stores no API key and no full reasoning."""

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
    content: str
    reasoning_chars: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0


def cache_key(model: str, messages: list[dict[str, str]], generation: dict[str, Any], prompt_version: str) -> str:
    payload = json.dumps({"model": model, "messages": messages, "generation": generation, "prompt_version": prompt_version},
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, model TEXT, content TEXT, "
            "reasoning_chars INTEGER, input_tokens INTEGER, output_tokens INTEGER, latency_s REAL, created_at TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> LLMResponse | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT content, reasoning_chars, input_tokens, output_tokens, latency_s FROM responses WHERE key = ?",
                (key,)).fetchone()
        return LLMResponse(*row) if row else None

    def put(self, key: str, model: str, response: LLMResponse) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (key, model, response.content, response.reasoning_chars, response.input_tokens,
                 response.output_tokens, response.latency_s, datetime.now(UTC).isoformat(timespec="seconds")))
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
