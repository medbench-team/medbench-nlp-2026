# Research: 004-llm-ceiling-ollama

Дата: 2026-11-17. Все проверки — живыми запросами к Ollama Cloud (единичные пробные вызовы,
без данных test), документация — через context7 (`/websites/langchain`,
`/websites/langchain_oss_python_langgraph`, `/websites/ollama_api`).

## R1. Каталог и выбранные модели

`GET https://ollama.com/v1/models` → 24 модели. Пробный запрос (одна пара NLI, temperature 0):

| Модель | Время | Рассуждение | Ответ |
|---|---|---|---|
| gemma4:31b | 0.4 с | нет | entailment ✓ |
| glm-5.3 | 0.8 с | да (~390 симв.) | ✓ |
| gpt-oss:120b | 1.0 с | да (~420 симв.) | ✓ |
| deepseek-v4-pro:0813 | 2.9 с | да (~1.4k симв.) | ✓ |
| kimi-k3.1-pro | 8.5 с | да | ✓ |
| mistral-large-4 | 17.2 с | да | ✓ |

**Decision** (clarify Q1 → B): по умолчанию `gpt-oss:120b`, `glm-5.3`, `deepseek-v4-pro:0813`,
`gemma4:31b`. Лимиты сервис в заголовках не сообщает → по умолчанию 4 параллельных запроса.

## R2. LangChain `ChatOllama` + Ollama Cloud (проверено, langchain-ollama 1.1.0)

- **Decision**: `ChatOllama(model=…, base_url="https://ollama.com", temperature=0,
  reasoning=True, client_kwargs={"headers": {"Authorization": f"Bearer {key}"}})`.
  - `reasoning=True` выносит рассуждение в `additional_kwargs["reasoning_content"]`, а
    `content` остаётся чистым ответом (без него рассуждение тоже идёт, но не возвращается).
  - Токены: `AIMessage.usage_metadata` (`input_tokens`, `output_tokens`).
  - `await llm.abatch(prompts, config={"max_concurrency": 4})` работает (8 запросов за 1.3 с).
- Ключ — из `.env` (`OLLAMA_API_KEY`); читается в процессе, в логи/кеш/прогоны не пишется.

## R3. Структурированный вывод в облаке НЕ работает (ADR-020, заменяет ADR-003)

- `with_structured_output(..., method="json_schema")` → `OutputParserException` на всех 4 моделях.
- Прямой `/api/chat` с `"format": <JSON schema>` и `"format": "json"` → модель отвечает свободным
  текстом («Отношение: **противоречие**. Объяснение: …»). Сервер Ollama Cloud игнорирует `format`.
- **Decision**: формат принуждается промптом («последняя строка: `Ответ: <метка>`»), разбор —
  собственным парсером `parse_answer(task, text)`, при неудаче — повтор с корректирующим
  сообщением (до 2 раз) в графе LangGraph; затем резервная метка с `invalid=true`.
- **Parser rules**: (1) строка `Ответ:`/`Answer:` → метка из неё; (2) иначе единственная
  упомянутая метка во всём ответе; канонизация: NLI — `entailment|следует|следование`,
  `contradiction|противоречие|противоречит`, `neutral|нейтрально|нейтральн…`; DaNet — `да|нет`
  (`yes|no`); RuMedTest — цифра 1–4. Несколько разных меток → `None` (невалидно).
- **Alternatives**: OpenAI-совместимый `/v1` с `response_format` — не проверен и вне требования
  «LangChain ChatOllama»; tool calling — избыточно для одной метки.

## R4. LangGraph-граф на пример (LangGraph 1.2.x)

`StateGraph(TypedDict)` с узлами `build_prompt → cache_lookup → call_llm → parse → validate`
и `add_conditional_edges`: попадание в кеш → `parse`; валиден → `END`; невалиден и попыток < N
→ `reprompt` → `call_llm`; иначе → `fallback` → `END`. Параллельность — `graph.abatch(inputs,
config={"max_concurrency": k})` (top-level ключ конфига, context7). Временные ошибки HTTP
(429/5xx/timeout) — повтор внутри `call_llm` с экспоненциальной паузой (1, 2, 4, 8, 16 с, до 5 раз).

## R5. Кеш ответов

- **Decision**: SQLite (stdlib `sqlite3`, WAL) в `data/llm_cache/cache.sqlite` (вне git).
  Ключ — sha256 от `{model, messages, params(temperature, reasoning, num_predict), prompt_version}`;
  значение — `content`, длина рассуждения, `usage`, `latency_s`, время. Повторный запуск той же
  конфигурации → 0 запросов (SC-002); продолжение после обрыва — бесплатно (US1-2).
- **Alternatives**: LangChain `SQLiteCache` (глобальный, кеширует по сериализации модели — менее
  прозрачно, не хранит латентность); JSONL (гонки при параллельной записи).

## R6. Промпты v1 (zero-shot, русский)

- NLI: роль «врач-эксперт», определения трёх отношений, посылка/гипотеза, требование последней
  строки `Ответ: entailment|contradiction|neutral`.
- DaNet: контекст + вопрос, «ответь на основе контекста», `Ответ: да|нет`.
- RuMedTest: вопрос + 4 пронумерованных варианта, «один верный», `Ответ: <номер>`.
- Резервные метки (`invalid=true`): NLI `neutral`, DaNet `да`, RuMedTest `1`.
- `num_predict=8192` (рассуждение + ответ), таймаут запроса 300 с.

## R7. Объём и время (оценка по R1, 4 потока)

«Подбор» на модель: 1 649 запросов (без повторов). gemma4 ~3 мин, glm-5.3 ~6 мин,
gpt-oss ~7 мин, deepseek ~20 мин → ~40 мин на 4 модели (SC-006 ≤ 2 ч на модель ✓).
Финал (2 модели × 1 678) и сабмит (2 445 на модель) — по выбору.

## R8. Зависимости

`langchain-ollama>=1.1` (тянет `ollama`, `langchain-core`), `langgraph>=1.2`. `.env` читается
собственной функцией (без `python-dotenv`).

## R9. Выбор моделей для финала (только по `tune`)

Записано **до** запуска `--role final`, по `reports/llm/ceiling.md` (открытый dev, zero-shot v1,
temperature 0, invalid 0% и call_errors 0 у всех четырёх моделей).

| Модель | NLI | DaNet | Среднее |
|---|---|---|---|
| glm-5.3 | **86.00** | **96.88** | **91.44** |
| gemma4:31b | 85.00 | 96.48 | 90.74 |
| gpt-oss:120b | 82.05 | 95.31 | 88.68 |
| deepseek-v4-pro:0813 | 78.82 | 94.92 | 86.87 |

- **Decision**: в финал идут **glm-5.3** и **gemma4:31b** (обе задачи, NLI и DaNet).
  Для `submit` (сабмит на сайт, включая RuMedTest) — glm-5.3, лучшая по среднему на tune.
- **Rationale**: эти две модели лучшие на tune по обеим задачам. Между ними 1.0 п.п. на NLI и
  0.4 п.п. на DaNet, это меньше стандартной ошибки (≈0.9 п.п. на 1393 примерах NLI, ≈1.1 п.п. на 256
  DaNet), поэтому на tune их нельзя надёжно различить. Финал обеих стоит 2 прогона, что в рамках
  принципа I (один final на конфигурацию). gemma4 к тому же примерно вдвое быстрее (2.2 с против 5.4 с на NLI).
- **Alternatives considered**: только glm-5.3 — отказались, потому что разница с gemma4 в пределах шума;
  все 4 модели — тоже нет: final без отбора по tune противоречит смыслу роли tune, и это лишние прогоны на test.
