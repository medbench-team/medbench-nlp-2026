# Data Model: 004-llm-ceiling-ollama

## LLMConfig (`configs/llm_ceiling.yaml`)

| Поле | Значение по умолчанию | Правила |
|---|---|---|
| `base_url` | `https://ollama.com` | |
| `models` | `[gpt-oss:120b, glm-5.3, deepseek-v4-pro:0813, gemma4:31b]` | проверяются по каталогу `/v1/models` до старта |
| `prompt_version` | `v1` | смена → новая конфигурация |
| `generation` | `{temperature: 0, reasoning: true, num_predict: 8192}` | |
| `concurrency` | 4 | 1…16 |
| `format_retries` | 2 | повторы при нераспознанном ответе |
| `http_retries` | 5 | экспоненциальная пауза 1→16 с |
| `timeout_s` | 300 | |
| `fallback` | `{RuMedNLI: neutral, RuMedDaNet: да, RuMedTest: 1}` | |

`params` прогона (→ `config_hash`) = `{prompt_version, generation, format_retries, fallback}`;
`approach = "llm-zero-shot"`, `model = <тег>`.

## ExampleState (состояние графа LangGraph)

| Поле | Тип | Описание |
|---|---|---|
| `task` | TaskName | NLI / DaNet / RuMedTest |
| `example` | Example | из `get_role` |
| `messages` | list | промпт (+ корректирующие сообщения) |
| `cache_key` | str | sha256 (R5) |
| `response` | LLMResponse \| None | |
| `label` | str \| int \| None | результат разбора |
| `attempts` | int | число вызовов модели (≤ 1 + `format_retries`) |
| `invalid` | bool | резервная метка поставлена |
| `usage` | dict | суммарно по попыткам: input/output tokens, latency_s, from_cache |

Переходы: `build_prompt → cache_lookup → (hit) parse | (miss) call_llm → parse → validate →
(ok) END | (bad, attempts ≤ format_retries) reprompt → cache_lookup | (bad) fallback → END`.

## LLMResponse (строка кеша SQLite)

`key` (PK, sha256), `model`, `content`, `reasoning_chars`, `input_tokens`, `output_tokens`,
`latency_s`, `created_at`. Без ключа доступа и без полного текста рассуждения.

## LLM run → Prediction / RunMeta (спека 002)

`Prediction(id, prediction=label, invalid, raw=content[:500] если invalid)`; `RunMeta.usage =
{input_tokens, output_tokens, latency_s_mean, cache_hits, requests}`; `invalid_rate` из
предсказаний. `--limit N` → прогон не сохраняется, печатаются метрики на подвыборке (FR-010).

## CeilingReport (`reports/llm/ceiling.md` + `.json`)

Таблица «модель × задача» по последним `tune`-прогонам `llm-zero-shot`: Acc, доля невалидных,
токены (вход/выход на пример), средняя задержка; строки бейзлайнов `naive`/`linear` (tune) и
previous art (open); лучшая модель по задаче, Δ к бейзлайну, вывод «LLM / энкодер / неясно».
