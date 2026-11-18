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
- `uv sync` — установить зависимости; `uv run pytest` — тесты (без сети); `uv run medbench <cmd>` — прогоны.
- LLM (спека 004): `uv run medbench llm models | run [--model M] [--task T] [--role R] [--limit N] | report`;
  ответы кешируются в `data/llm_cache/` (повтор бесплатный); облако **игнорирует `format`/JSON-схему** —
  формат ответа держит промпт + `medbench.llm.parse` (ADR-020); ключ `OLLAMA_API_KEY` только в `.env`.
- Бейзлайны: `uv run medbench baselines run [--role tune|final|submit]`, `uv run medbench baselines report`
  (≈ 7 мин на роль, пик 1.2 ГБ RAM — реальные прогоны запускать по одному).
- Данные: `uv run medbench data download | verify | overlap | stats`; в коде — только
  `medbench.data.get_role(task, role)` с ролями `train` / `tune` / `final` / `submit` (не читать файлы напрямую).
- LLM: Ollama Cloud (`https://ollama.com`) через `langchain-ollama` `ChatOllama`, оркестрация —
  LangGraph. Ключ `OLLAMA_API_KEY` в `.env`.
- На сервере **нет GPU** (2 CPU, ~3 ГБ RAM): обучение энкодеров/LoRA — Colab/Kaggle; в репо —
  ноутбуки и `preds.jsonl`. Тяжёлые модели локально не запускать.

## Данные и оценка

- Единственный источник примеров — открытый RuMedBench @ `dd57f4f` (`configs/data.yaml`).
- `data/MedBench_data/` — версия сайта, только для сверки: **dev сайта = открытый test**, test сайта =
  открытый `private_test`. Не в git.
- Подбор моделей, промптов и гиперпараметров — **только по роли `tune` (открытый dev)**. Открытый test — один
  финальный прогон на конфигурацию. Метки test для подбора не использовать никогда.
- Метрики и Overall — ровно как в официальном `code/eval.py` (`medbench.eval`, проверка —
  `uv run medbench eval paper`). Результаты сохранять **только** через `medbench.eval.save_run`
  (`results/runs/<run_id>/`); на `final` — один прогон на конфигурацию, повтор только с обоснованием.
- Previous art: `configs/previous_art.yaml`; open test и закрытый test сайта не смешивать (ADR-016).

## Безопасность

- Секреты только в `.env`; не коммить, не выводить в логи и ответы.
- `data/`, `context/`, `.env` в `.gitignore` — не добавлять их в индекс.
- `context/` — личные материалы курса (описание проекта, статья, шаблон отчёта, `PLAN.md`);
  читать можно, коммитить нельзя.

## Язык

Документы, спеки и общение — на русском. Код, идентификаторы, коммиты и названия веток — на
английском.
