# Implementation Plan: Бейзлайны — Naive и TF-IDF/CRF, воспроизведение статьи

**Branch**: `003-baselines` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-baselines/spec.md`

**Klyaksa**: проект «MedBench», холст **«003 baselines»** (`696157e7-7db2-4631-8567-61f907f3988f`);
ADR-018, ADR-019 на «03 Decisions (ADR)».

## Summary

Подпакет `medbench.baselines` с двумя подходами — `naive` (правила восстановлены по официальным
предсказаниям, research R2) и `linear` (TF-IDF char 3–8 + OneVsRest LogReg C=10; CRF для NER —
гиперпараметры `code/linear_models`, research R1, R3, R4). Каждый подход обучается один раз на
роли `train` и предсказывает запрошенные роли (`tune` по умолчанию, `final`/`submit` явно);
результаты сохраняются только через `medbench.eval.save_run` с общим для всех задач `params`
(одна конфигурация → Overall в сводке). Команда `baselines report` сравнивает финальные прогоны
с опубликованными Naive и TF-IDF. Замер: 5 задач за ~7 мин при пике 1.2 ГБ RAM (research R5).

## Technical Context

**Language/Version**: Python 3.12, uv

**Primary Dependencies**: + `scikit-learn>=1.9` (TfidfVectorizer, LogisticRegression,
OneVsRestClassifier), + `python-crfsuite>=0.9.12`; остальное — спеки 001–002

**Storage**: прогоны — `results/runs/` (через спеку 002); отчёт — `reports/baselines/reproduction.{md,json}`;
модели не сохраняются (CRF — во временный файл)

**Testing**: pytest на фикстурах спеки 001 (минимальные train/dev/test) — проверка формата
предсказаний и интеграции с `save_run`; полное воспроизведение — команды на реальных данных

**Target Platform**: Linux-сервер (2 CPU, ~3 ГБ RAM), без GPU

**Project Type**: библиотека + CLI (`uv run medbench baselines …`)

**Performance Goals**: все роли пяти задач < 30 мин (SC-003); фактически ~7 мин на роль

**Constraints**: пик памяти ≤ 1.5 ГБ; `n_jobs ≤ 2`; фиксированный сид

**Scale/Scope**: 2 подхода × 5–6 задач × до 3 ролей

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Как выполняется | Статус |
|---|---|---|
| I. Честная оценка | Обучение только на `train` (без дубликатов test); гиперпараметры из статьи, без подбора; `final` только явным флагом и один раз; эксперименты research — на `tune` (единственная проверка Naive NER на test — для стратегии previous art, не нашего подхода) | ✅ |
| II. Воспроизводимость | Полные `params` в `meta.json`; сид 128; детерминированные решатели | ✅ |
| III. Сравнимость | Гиперпараметры `code/linear_models`; отчёт «наше / статья / Δ» с причинами расхождений | ✅ |
| IV. Визуализация | Холст «003 baselines», ADR-018/019 | ✅ |
| V. Простота | 2 новые зависимости, обоснованы (R3, R4); без обёртки sklearn-crfsuite и pandas | ✅ |
| VI. Тесты | pytest на формат предсказаний, naive-правила, интеграцию с `save_run`, без сети | ✅ |

Повторная проверка после Phase 1: нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/003-baselines/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/baselines-cli.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/medbench/baselines/
├── __init__.py          # NaiveBaseline, LinearBaseline, run_baselines, build_reproduction_report
├── base.py              # протокол Baseline, тексты входов по задачам
├── naive.py             # правила research R2
├── linear.py            # TF-IDF + OvR LR; CRF (python-crfsuite) для NER
├── runner.py            # fit один раз → predict по ролям → save_run; skip-логика
├── report.py            # reports/baselines/reproduction.{md,json}
└── commands.py          # typer: run, report
src/medbench/cli.py      # + app.add_typer(baselines_app, name="baselines")
reports/baselines/       # отчёт о воспроизведении (git)
tests/
├── test_baselines_naive.py
├── test_baselines_linear.py   # на фикстурах: формат, top-3 различные, длины NER
└── test_baselines_runner.py   # роли, skip, final один раз, интеграция с save_run
```

**Structure Decision**: подпакет `medbench.baselines`; CLI-группа `baselines`.

## Complexity Tracking

Нарушений конституции нет.
