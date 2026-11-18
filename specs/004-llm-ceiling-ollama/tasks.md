---

description: "Task list for 004-llm-ceiling-ollama"
---

# Tasks: Потолок LLM — крупнейшие облачные модели zero-shot на NLI, DaNet, RuMedTest

**Input**: Design documents from `specs/004-llm-ceiling-ollama/`

**Prerequisites**: plan.md, spec.md (clarify: 4 модели), research.md, data-model.md,
contracts/llm-cli.md, quickstart.md; спеки 001–003 реализованы

**Tests**: включены (конституция, принцип VI); без сети — фейковая chat-модель.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US3 из spec.md

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Добавить зависимости `uv add "langchain-ollama>=1.1" "langgraph>=1.2"` (`pyproject.toml`, `uv.lock`); перед кодом сверить API `ChatOllama`, `StateGraph`, `add_conditional_edges`, `abatch(config={"max_concurrency": …})` через context7 (как в research.md R2, R4)
- [X] T002 Создать подпакет `src/medbench/llm/` (`__init__.py`, `commands.py` с `llm_app = typer.Typer(help="LLM ceiling: Ollama Cloud via LangChain + LangGraph.", no_args_is_help=True)`) и подключить в `src/medbench/cli.py` (`app.add_typer(llm_app, name="llm")`); добавить `/data/` уже игнорируется — проверить `git check-ignore data/llm_cache`
- [X] T003 [P] Создать `configs/llm_ceiling.yaml` по data-model.md: `base_url: https://ollama.com`, `models: [gpt-oss:120b, glm-5.3, deepseek-v4-pro:0813, gemma4:31b]`, `prompt_version: v1`, `generation: {temperature: 0, reasoning: true, num_predict: 8192}`, `concurrency: 4` («1…16»), `format_retries: 2`, `http_retries: 5`, `timeout_s: 300`, `fallback: {RuMedNLI: neutral, RuMedDaNet: да, RuMedTest: 1}`, `cache_path: data/llm_cache/cache.sqlite`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: конфиг, ключ, промпты, парсер, кеш, граф — нужны всем историям

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Реализовать `LLMConfig` (pydantic, поля и ограничения из data-model.md) и `load_llm_config(path)` в `src/medbench/llm/config.py`; `api_key()` — из `os.environ["OLLAMA_API_KEY"]`, иначе из `.env` в корне (простой разбор `KEY=VALUE`, кавычки, комментарии), иначе `MissingApiKeyError` с текстом без значения ключа; `run_params(config)` → `{prompt_version, generation, format_retries, fallback}` (вход `config_hash`)
- [X] T005 [P] Реализовать промпты v1 в `src/medbench/llm/prompts.py` по research.md R6: `build_messages(task, example) -> list[dict(role, content)]` для RuMedNLI (определения entailment/contradiction/neutral, посылка/гипотеза), RuMedDaNet (контекст + вопрос, ответ по контексту), RuMedTest (вопрос + 4 пронумерованных варианта); во всех — требование «последняя строка: `Ответ: <метка>`» с перечнем допустимых меток; `correction_message(task)` — короткое напоминание формата для повтора
- [X] T006 [P] Реализовать `parse_answer(task, text) -> str | int | None` в `src/medbench/llm/parse.py` по research.md R3: (1) последняя строка вида `Ответ:`/`Answer:` (регистронезависимо, с markdown `**`) → метка из неё; (2) иначе единственная упомянутая метка во всём тексте; синонимы NLI `entailment|следует|следование|вытекает`, `contradiction|противоречие|противоречит`, `neutral|нейтрально|нейтральн\w*`; DaNet `да|нет|yes|no`; RuMedTest — цифра 1–4 (в т.ч. `2)`, `вариант 2`); несколько разных меток → `None`; пустой текст → `None`
- [X] T007 [P] Реализовать SQLite-кеш в `src/medbench/llm/cache.py` по research.md R5: файл `data/llm_cache/cache.sqlite` (WAL), таблица `responses(key PK, model, content, reasoning_chars, input_tokens, output_tokens, latency_s, created_at)`; `cache_key(model, messages, generation, prompt_version)` — sha256 канонического JSON; `get(key)`, `put(key, LLMResponse)`; потокобезопасно для asyncio (одно соединение + `asyncio.Lock` или `check_same_thread=False`); ключ доступа не хранится
- [X] T008 Реализовать провайдер в `src/medbench/llm/provider.py`: `make_chat(model, config) -> ChatOllama(model, base_url, temperature, reasoning, num_predict, client_kwargs={"headers": {"Authorization": f"Bearer {key}"}, "timeout": timeout_s})`; `async call(chat, messages) -> LLMResponse` с повтором при 429/5xx/таймауте (экспоненциальная пауза 1→16 с, `http_retries`), `usage_metadata` → токены, `additional_kwargs["reasoning_content"]` → только длина; `list_cloud_models(config)` — `GET {base_url}/v1/models` с ключом
- [X] T009 Реализовать граф в `src/medbench/llm/graph.py` по data-model.md (`ExampleState`) и research.md R4: `StateGraph` с узлами `build_prompt`, `cache_lookup`, `call_llm`, `parse`, `validate`, `reprompt`, `fallback`; `add_conditional_edges`: попадание в кеш → `parse`; валидно → `END`; невалидно и `attempts ≤ format_retries` → `reprompt` (добавить ответ модели и `correction_message`) → `cache_lookup`; иначе → `fallback` (метка из `config.fallback`, `invalid=True`) → `END`; суммирование `usage` по попыткам; `build_graph(chat, cache, config)` и `async run_examples(graph, task, examples, concurrency) -> list[ExampleResult]` через `graph.abatch(..., config={"max_concurrency": concurrency})`
- [X] T010 [P] Тесты `tests/test_llm_parse.py`: табличные случаи из research.md R3 (строка `Ответ: **entailment**`, русские синонимы, «противоречие (contradiction)», несколько меток → None, DaNet `Да.`, RuMedTest `Ответ: 2`, `вариант 3`, `5` → None, пустой ответ)
- [X] T011 [P] Тесты `tests/test_llm_cache.py`: ключ стабилен к порядку ключей и меняется от модели/сообщений/версии промпта; put/get туда-обратно; файл во `tmp_path`; в БД нет строки ключа доступа
- [X] T012 Тесты `tests/test_llm_graph.py` с фейковой моделью (подмена `call` на корутину-заглушку со сценариями): валидный ответ с первой попытки; невалидный → повтор → валидный (attempts=2); всегда невалидный → fallback, `invalid=True`, attempts = 1 + `format_retries`; повторный прогон тех же примеров → 0 вызовов модели (всё из кеша); параллельный прогон 20 примеров с `concurrency=4`

**Checkpoint**: граф работает офлайн на заглушке

---

## Phase 3: User Story 1 — Потолок на «подборе» (Priority: P1) 🎯 MVP

**Goal**: `uv run medbench llm run` (4 модели × NLI, DaNet, `tune`) + отчёт о потолке

**Independent Test**: `llm run --model gemma4:31b --limit 20` даёт метрики без сохранения; полный прогон → 8 tune-прогонов с invalid ≤ 2%; `llm report` → `reports/llm/ceiling.md`

- [X] T013 [P] [US1] Тесты `tests/test_llm_runner.py` (заглушка модели, `results_dir` во `tmp_path`): прогон сохраняется через `save_run` с `approach="llm-zero-shot"`, `model=<тег>`, `params` из `run_params`, `usage = {input_tokens, output_tokens, latency_s_mean, cache_hits, requests}`; `limit` → без сохранения, печать метрик подвыборки; RuMedTest вне `submit` → `skip`; повторный `final` → `skip`
- [X] T014 [US1] Реализовать `run_llm(models, tasks, roles, limit=None, justification=None, config=…, results_dir=…, on_progress=None)` в `src/medbench/llm/runner.py`: проверка моделей по каталогу до старта (`list_cloud_models`), для каждой (модель, задача, роль) — `get_role` → `run_examples` → `Prediction(id, prediction=label, invalid, raw=content[:500] если invalid)` → `save_run` (или метрики подвыборки при `limit`); прогресс каждые 50 примеров (done/total, cache hits, invalid)
- [X] T015 [US1] Реализовать отчёт о потолке в `src/medbench/llm/report.py` по data-model.md (`CeilingReport`): последние `tune`-прогоны `llm-zero-shot` по моделям × задачам (Acc, invalid %, токены вход/выход на пример, средняя задержка), строки `naive`/`linear` (tune) и previous art (open) из `configs/previous_art.yaml`, лучшая модель по задаче, Δ к `linear`, вывод по задаче; запись `reports/llm/ceiling.{md,json}`
- [X] T016 [US1] Добавить команды `models`, `run` (опции из contracts/llm-cli.md), `report` в `src/medbench/llm/commands.py`; экспорт API в `src/medbench/llm/__init__.py`
- [X] T017 [US1] Дымовой прогон на реальном облаке: `uv run medbench llm models`, затем `uv run medbench llm run --model gemma4:31b --limit 20`; проверить долю невалидных и формат ответов; при необходимости поправить промпт **до** полного прогона (версия остаётся `v1`, т.к. сохранённых прогонов ещё нет)
- [X] T018 [US1] Полный прогон на `tune`: `uv run medbench llm run` (4 модели × NLI, DaNet) — в фоне, с замером времени; затем повтор той же команды → 0 новых запросов (SC-002); `uv run medbench llm report` и `uv run medbench eval leaderboard` (SC-001, SC-003, SC-006)

**Checkpoint**: потолок на dev измерен, отчёт готов

---

## Phase 4: User Story 2 — Финальный прогон лучших моделей (Priority: P1)

**Goal**: один `final` для 1–2 лучших по `tune` моделей на NLI и DaNet

**Independent Test**: финальные строки LLM в `results/leaderboard.md` с Δ к previous art; повтор без `--justification` → `skip`

- [X] T019 [US2] Выбрать 1–2 лучшие модели **только по `reports/llm/ceiling.md` (tune)**, записать выбор и обоснование в `specs/004-llm-ceiling-ollama/research.md` (раздел R9) до запуска финала
- [X] T020 [US2] Запустить `uv run medbench llm run --model <выбранные> --role final` (NLI, DaNet); обновить `uv run medbench eval leaderboard`; проверить повторный запуск → `skip` (SC-004)

**Checkpoint**: потолок LLM сопоставлен с previous art на open test

---

## Phase 5: User Story 3 — RuMedTest и сабмит (Priority: P2)

**Goal**: submit-прогоны лучшей модели для RuMedTest, DaNet, NLI и архив

**Independent Test**: `uv run medbench eval submit --run …` из LLM-прогонов — без предупреждений

- [ ] T021 [US3] Запустить `uv run medbench llm run --model <лучшая> --task RuMedTest --task RuMedNLI --task RuMedDaNet --role submit`; проверить, что ответы RuMedTest — 1–4 и доля невалидных ≤ 2%
- [ ] T022 [US3] Собрать `uv run medbench eval submit --run <RuMedDaNet> --run <RuMedNLI> --run <RuMedTest>` из LLM-прогонов (SC-005); архив — в `results/submissions/` (вне git)

**Checkpoint**: сабмит с LLM готов к загрузке на сайт

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Обновить `README.md` (раздел «Потолок LLM»: команды, таблица из `reports/llm/ceiling.md`) и `CLAUDE.md` (команды `llm`, кеш, ключ только в `.env`)
- [ ] T024 Пройти `specs/004-llm-ceiling-ollama/quickstart.md`; `uv run pytest` без сети (`unshare -rn`); проверить, что ключ не встречается в `results/`, `reports/`, `data/llm_cache/` (`grep -r` по значению из `.env`)
- [ ] T025 Обновить Klyaksa: холст «004 LLM ceiling» — итоговая таблица потолка и вывод «LLM / энкодер» по задачам; ADR при новых решениях; после мержа — 004 зелёным на «00 Roadmap», ✅ в `docs/ROADMAP.md` и `context/PLAN.md`

---

## Dependencies & Execution Order

- Setup → Foundational (T004–T012) → истории.
- **US1** зависит от Phase 2. MVP.
- **US2** зависит от US1 (выбор модели по отчёту `tune`).
- **US3** зависит от US1 (выбор модели); от US2 не зависит.
- Polish — в конце.

### Parallel Opportunities

- Phase 1: T003 параллельно с T001–T002.
- Phase 2: T005, T006, T007 параллельно (разные файлы); тесты T010, T011 параллельно.
- Реальные прогоны (T017, T018, T020, T021) — последовательно: общий лимит облака.

## Parallel Example: Phase 2

```bash
Task: "T005 Промпты в src/medbench/llm/prompts.py"
Task: "T006 Парсер в src/medbench/llm/parse.py"
Task: "T007 Кеш в src/medbench/llm/cache.py"
```

## Implementation Strategy

### MVP First

1. Setup + Foundational → граф проверен офлайн.
2. US1: дымовой прогон → полный `tune` → отчёт о потолке — главный ответ спеки.

### Incremental Delivery

1. US1 → потолок на dev и вывод «LLM / энкодер».
2. US2 → один финал лучших моделей против previous art.
3. US3 → сабмит RuMedTest — главный кандидат на SotA (35.0 на сайте).

## Notes

- Ключ `OLLAMA_API_KEY` только в `.env`; ни в коде, ни в логах, ни в кеше.
- Выбор модели для финала — только по `tune` (принцип I).
- Реальные запросы к облаку — T017, T018, T020, T021; тесты — без сети.
