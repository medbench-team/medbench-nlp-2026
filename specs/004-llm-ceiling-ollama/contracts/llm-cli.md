# Contract: CLI и API LLM-прогонов

## CLI (`uv run medbench llm <cmd>`)

| Команда | Что делает | Код выхода |
|---|---|---|
| `llm models` | Каталог Ollama Cloud; отмечает модели из конфига как доступные/нет | 0 / 1 (нет ключа, сеть) |
| `llm run [--model M ...] [--task T ...] [--role tune\|final\|submit ...] [--limit N] [--concurrency K] [--justification TEXT]` | Прогон графа по примерам; по умолчанию — все модели конфига, NLI+DaNet, `tune`. С `--limit` — без сохранения | 0 / 1 |
| `llm report` | `reports/llm/ceiling.{md,json}` | 0 / 1 (нет прогонов) |

Вывод `run`: прогресс по модели/задаче (`done/total`, кеш-попадания, невалидные), затем
`model task role → acc=… invalid=…% tokens in/out=… latency=…s | saved <run_id>`.

## Python API (`medbench.llm`)

```python
load_llm_config(path="configs/llm_ceiling.yaml") -> LLMConfig
build_graph(chat, cache, config) -> CompiledStateGraph          # R4
async run_examples(model, task, examples, config) -> list[ExampleResult]
run_llm(models, tasks, roles, limit=None, justification=None) -> list[RunOutcome]
parse_answer(task, text) -> str | int | None                     # R3
build_ceiling_report() -> CeilingReport
```

Ключ доступа читается из окружения или `.env`; `MissingApiKeyError` без вывода значения.
