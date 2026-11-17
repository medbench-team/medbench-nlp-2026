# CLAUDE.md

Инструкции для Claude Code в этом репозитории.

## О проекте

Курсовой проект NLP (ITMO AI Talent Hub, осень 2026): SotA на русскоязычном медицинском
бенчмарке **RuMedBench** — RuMedNLI, RuMedDaNet, RuMedTest (ядро), RuMedNER / RuMedTop3 /
RuMedSymptomRec (расширение). Сравниваемся с previous art на открытом test RuMedBench.

- Дорожная карта и статусы спек: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- Правила (обязательны): [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Git-процесс: [`GITFLOW.md`](GITFLOW.md)

## Как ведём разработку

1. **Только через GitHub Spec Kit**, спека за спекой по `docs/ROADMAP.md`:
   `/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` →
   (`/speckit-analyze`) → `/speckit-implement`.
2. Одна спека = одна ветка `NNN-short-name` от `dev` = один PR в `dev`. Не коммить и не пушить
   в `main` и `dev` напрямую.
3. После мержа спеки обнови её статус в `docs/ROADMAP.md` и цвет блока на холсте «00 Roadmap».

## Klyaksa — схемы решений (обязательно)

Проект **MedBench** в Klyaksa (MCP `klyaksa`). Перед первым использованием в сессии вызови
`get_manual`.

- У каждой спеки свой холст `NNN <name>`: нарисуй, как реализована фича (модули, поток данных,
  граф), **во время `/speckit-plan`**, и укажи холст в `plan.md`.
- Каждое новое архитектурное или методологическое решение — стикер `ADR-NNN` («решение ·
  почему») на холсте «03 Decisions (ADR)». Отменённые решения не удаляй — перекрась в серый.
- Изменилась архитектура — обнови «01 Architecture»; изменились данные или правила оценки —
  «02 Data & Evaluation».
- Рисуй через `draw_skeleton`, проверяй `check_layout` и скриншотом, сохраняй
  `version_write action=save`. Исправляй существующие элементы, а не рисуй копию рядом.
- ID холстов — в `docs/ROADMAP.md`, раздел «Схемы в Klyaksa».

## context7 — документация библиотек (обязательно)

Перед написанием кода с API библиотек (LangChain, LangGraph, langchain-ollama, Ollama,
transformers, datasets, scikit-learn, pydantic, typer) сверяйся с context7
(`resolve-library-id` → `query-docs`). Не полагайся на память: эти API быстро меняются.

## Стек и команды

- Python 3.12, `uv`, src-layout `src/medbench/`, CLI на typer.
- `uv sync` — установить зависимости; `uv run pytest` — тесты; `uv run medbench <cmd>` — прогоны.
- LLM: Ollama Cloud (`https://ollama.com`) через `langchain-ollama` `ChatOllama`, оркестрация —
  LangGraph. Ключ `OLLAMA_API_KEY` в `.env`.
- На сервере **нет GPU** (2 CPU, ~3 ГБ RAM): обучение энкодеров/LoRA — Colab/Kaggle; в репо —
  ноутбуки и `preds.jsonl`. Тяжёлые модели локально не запускать.

## Данные и оценка

- `data/MedBench_data/` — версия с сайта medbench.ru, **test без меток**. Не в git.
- Открытый RuMedBench (github.com/sb-ai-lab/MedBench) — test с метками, на нём previous art.
- Подбор моделей, промптов и гиперпараметров — **только по dev**. Открытый test — один
  финальный прогон на конфигурацию. Метки test для подбора не использовать никогда.
- Метрики и Overall — ровно как в статье RuMedBench. Все подходы пишут единый
  `results/<run_id>/preds.jsonl` + `meta.json`.

## Безопасность

- Секреты только в `.env`; не коммить, не выводить в логи и ответы.
- `data/`, `context/`, `.env` в `.gitignore` — не добавлять их в индекс.
- `context/` — личные материалы курса (описание проекта, статья, шаблон отчёта, `PLAN.md`);
  читать можно, коммитить нельзя.

## Язык

Документы, спеки и общение — на русском. Код, идентификаторы, коммиты и названия веток — на
английском.
