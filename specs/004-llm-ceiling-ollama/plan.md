# Implementation Plan: Потолок LLM — крупнейшие облачные модели zero-shot на NLI, DaNet, RuMedTest

**Branch**: `004-llm-ceiling-ollama` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-llm-ceiling-ollama/spec.md`

**Klyaksa**: проект «MedBench», холст **«004 LLM ceiling (Ollama + LangGraph)»**
(`691a83e8-0946-4fb2-8c89-9a265eec5690`), обновлён; ADR-020 (заменяет ADR-003) на «03 Decisions (ADR)».

## Summary

Подпакет `medbench.llm`: LangChain `ChatOllama` к Ollama Cloud (`base_url=https://ollama.com`,
Bearer-ключ из `.env`, `temperature=0`, `reasoning=True`) и граф LangGraph на каждый пример
(`build_prompt → cache_lookup → call_llm → parse → validate → reprompt/fallback`), параллельно
через `graph.abatch(max_concurrency=4)`. Главная находка research: **облако игнорирует
`format`/JSON-схему**, поэтому формат ответа принуждается промптом (`Ответ: <метка>`),
собственным парсером с русскими синонимами и до двух повторов (ADR-020). Ответы кешируются в
SQLite вне git — повтор без запросов, продолжение после обрыва. Результаты — через
`medbench.eval.save_run` (approach `llm-zero-shot`); отчёт `reports/llm/ceiling.md` сравнивает
4 модели (clarify: gpt-oss:120b, glm-5.3, deepseek-v4-pro:0813, gemma4:31b) с бейзлайнами и
previous art.

## Technical Context

**Language/Version**: Python 3.12, uv

**Primary Dependencies**: + `langchain-ollama>=1.1` (ChatOllama), + `langgraph>=1.2` (StateGraph);
stdlib `sqlite3`, `asyncio` (research R2, R4, R5, R8; сверено с context7 и живыми вызовами)

**Storage**: кеш `data/llm_cache/cache.sqlite` (вне git); прогоны `results/runs/` (спека 002);
отчёт `reports/llm/ceiling.{md,json}`; конфиг `configs/llm_ceiling.yaml`

**Testing**: pytest без сети — парсер (табличные случаи из R3), граф и кеш с фейковой
chat-моделью (`langchain_core` `GenericFakeChatModel` или собственная заглушка), раннер с
`save_run` во `tmp_path`

**Target Platform**: Linux-сервер (сеть к ollama.com), CPU-only

**Project Type**: библиотека + CLI (`uv run medbench llm …`)

**Performance Goals**: «подбор» одной модели ≤ 2 ч (оценка: 3–20 мин), повтор из кеша < 1 мин

**Constraints**: ключ никогда не логируется; неизвестные лимиты → 4 потока + экспоненциальная
пауза; финал только для 1–2 лучших моделей

**Scale/Scope**: 4 модели × (1 649 tune + опционально 1 678 final + 2 445 submit) запросов

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Как выполняется | Статус |
|---|---|---|
| I. Честная оценка | Выбор модели/промпта только по `tune`; `final` — явным флагом и один раз; research — без данных test | ✅ |
| II. Воспроизводимость | `temperature=0`, версия промпта в `params`, кеш ответов, токены/задержка в `meta.json` | ✅ |
| III. Сравнимость | Метрики и сохранение — через спеку 002; отчёт рядом с бейзлайнами и previous art | ✅ |
| IV. Визуализация | Холст 004 обновлён по факту (парсер вместо structured output), ADR-020 | ✅ |
| V. Простота | 2 зависимости, требуемые пользователем (LangChain/LangGraph); кеш на stdlib sqlite | ✅ |
| VI. Тесты | Без сети: парсер, граф, кеш, раннер на фейковой модели | ✅ |
| Секреты | Ключ из `.env`, не попадает в кеш/логи/прогоны (FR-008) | ✅ |

Повторная проверка после Phase 1: нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-ceiling-ollama/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/llm-cli.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
configs/llm_ceiling.yaml           # модели, промпт v1, генерация, параллельность, повторы, fallback
src/medbench/llm/
├── __init__.py                    # публичный API
├── config.py                      # LLMConfig (pydantic) + чтение ключа из env/.env
├── provider.py                    # ChatOllama для облака; список моделей каталога
├── prompts.py                     # шаблоны v1 для NLI / DaNet / RuMedTest
├── parse.py                       # parse_answer + корректирующее сообщение
├── cache.py                       # SQLite-кеш ответов
├── graph.py                       # LangGraph StateGraph на пример
├── runner.py                      # модели × задачи × роли → save_run; --limit
├── report.py                      # reports/llm/ceiling.{md,json}
└── commands.py                    # typer: models, run, report
src/medbench/cli.py                # + app.add_typer(llm_app, name="llm")
reports/llm/                       # отчёт о потолке (git)
tests/
├── test_llm_parse.py
├── test_llm_cache.py
├── test_llm_graph.py              # фейковая модель: валидный, повтор, fallback, кеш
└── test_llm_runner.py
```

**Structure Decision**: подпакет `medbench.llm`, CLI-группа `llm`.

## Complexity Tracking

Нарушений конституции нет.
