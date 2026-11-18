# Implementation Plan: Харнесс оценки — метрики как в статье, реестр прогонов, сабмит

**Branch**: `002-eval-harness` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-eval-harness/spec.md`

**Klyaksa**: проект «MedBench», холст **«002 eval-harness»**
(`9aa75117-eef6-4cd3-bb6c-42951122cb0e`); ADR-015…017 на «03 Decisions (ADR)».

## Summary

Подпакет `medbench.eval` — единственный путь, которым подходы 003–009 сохраняют и оценивают
результаты. Метрики повторяют формулы официального `code/eval.py` (Acc, Hit@3, потокенная Acc и
micro-F1 по сущностям для NER, Overall по 5 задачам) и реализованы на чистом Python; совпадение
с таблицей 3 статьи до сотых проверено на предсказаниях моделей статьи и закрепляется командой
`medbench eval paper` (research R2–R3). Прогон — `results/runs/<run_id>/{preds.jsonl,meta.json}`
в git; правило «один final на (config_hash, task)». Сводная таблица разделяет previous art на
open test и закрытый test сайта (ADR-016). Сабмит для medbench.ru собирается в формате
`sample_submission.zip`.

## Technical Context

**Language/Version**: Python 3.12, uv, src-layout (каркас из спеки 001)

**Primary Dependencies**: новых нет — stdlib (`json`, `hashlib`, `zipfile`, `subprocess`) +
уже имеющиеся pydantic, typer, pyyaml (research R7)

**Storage**: `results/runs/<run_id>/` (git), `results/leaderboard.{md,json}` (git),
`results/submissions/*.zip` (вне git), `configs/previous_art.yaml`, `configs/paper_outputs.yaml`
(git); кеш предсказаний статьи — `data/paper_outputs/<commit>/` (вне git)

**Testing**: pytest, без сети; фикстуры — ручные примеры для метрик и маленькие наборы
предсказаний; полная сверка со статьёй — тест с маркером `data` и команда `eval paper`

**Target Platform**: Linux-сервер, ноутбуки участников, Colab (импорт `medbench.eval`)

**Project Type**: библиотека + CLI (`uv run medbench eval …`)

**Performance Goals**: оценка любой задачи < 1 с; сводка по 100 прогонам < 10 с (SC-003)

**Constraints**: точное совпадение формул с `code/eval.py` (≤ 0.01 п.п.); тесты без сети;
`final` не перезаписывается

**Scale/Scope**: 6 задач, ~десятки–сотни прогонов за проект

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Как выполняется | Статус |
|---|---|---|
| I. Честная оценка | `score` только для `tune`/`final`; правило «один final на (config_hash, task)» с обязательным обоснованием повтора; `submit` не оценивается локально | ✅ |
| II. Воспроизводимость | `meta.json` с config, `code_commit` (+dirty), `data_commit`, датой; `eval rescore`; прогоны в git | ✅ |
| III. Сравнимость | Формулы `code/eval.py`, сверка с таблицей 3 до 0.01 (`eval paper`); previous art с пометкой open/site | ✅ |
| IV. Визуализация | Холст «002 eval-harness», ADR-015…017 | ✅ |
| V. Простота | Ноль новых зависимостей; один `save_run` для всех подходов | ✅ |
| VI. Тесты | pytest на метрики (ручные примеры, IOB-разбор), валидацию, реестр, сабмит; без сети | ✅ |

Повторная проверка после Phase 1: нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/002-eval-harness/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/eval-api.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
configs/
├── previous_art.yaml          # previous art с источником и test: open|site
└── paper_outputs.yaml         # предсказания моделей статьи: пути, sha256, ожидаемые метрики
src/medbench/eval/
├── __init__.py                # публичный API: score, overall, save_run, load_run, …
├── predictions.py             # Prediction, чтение/запись preds.jsonl, валидация против роли
├── metrics.py                 # accuracy, hit_at_3, ner_entities (IOB как seqeval), ner_f1, overall
├── runs.py                    # RunMeta, save_run/load_run, config_hash, правило final, git-коммит
├── leaderboard.py             # сводные таблицы final / tune / site
├── submission.py              # zip для medbench.ru + проверка
├── paper.py                   # скачивание предсказаний статьи и сверка (eval paper)
└── commands.py                # typer: score, save, rescore, leaderboard, submit, paper
src/medbench/cli.py            # + app.add_typer(eval_app, name="eval")
results/
├── runs/                      # прогоны (git)
├── leaderboard.md / .json     # сводка (git)
└── submissions/               # zip (вне git)
tests/
├── test_metrics.py            # формулы, IOB-разбор, Overall
├── test_predictions.py        # валидация против роли
├── test_runs.py               # save/load/rescore, правило final, stale data
├── test_leaderboard.py
├── test_submission.py
└── test_paper.py              # @pytest.mark.data — полная сверка с таблицей 3
```

**Structure Decision**: подпакет `medbench.eval` рядом с `medbench.data`; CLI-группа `eval`.

## Post-design notes

- `docs/ROADMAP.md`: previous art разделён на open test / site test (DaNet open SotA = 76.17,
  не 89.3), «macro-F1» → «NER micro-F1», статус 002 — 🟦, добавлен холст 002.
- Обнаружено: каталог `code/bert` официального репозитория = строка RuPoolBERT, не RuBERT.
- Ветка: работа идёт на `001-data-pipeline`, т.к. 001 ещё не закоммичена; перед реализацией —
  закоммитить 001 и создать `002-eval-harness` от неё.

## Complexity Tracking

Нарушений конституции нет.
