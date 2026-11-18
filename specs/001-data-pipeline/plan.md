# Implementation Plan: Данные RuMedBench — загрузка, канонические сплиты, EDA

**Branch**: `001-data-pipeline` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-data-pipeline/spec.md`

**Klyaksa**: проект «MedBench», холст **«001 data-pipeline»**
(`f271f48c-fff4-495c-98a9-afa48a2bad09`); решения ADR-012, ADR-013 на «03 Decisions (ADR)»;
обновлён «02 Data & Evaluation».

## Summary

Первая спека закладывает пакет `medbench` и слой данных для всех следующих спек. Открытые
файлы RuMedBench скачиваются с зафиксированного коммита `dd57f4f` и проверяются по sha256,
строки валидируются в единые pydantic-модели (дискриминированное объединение по задаче).
`get_role(task, role)` выдаёт сплиты по ролям train/tune/final/submit с проверкой утечек.
Данные сайта используются только для отчёта о пересечениях: исследование показало, что dev
сайта — это открытый test, а test сайта побайтово равен открытому `private_test`
([research.md](research.md) R2). Плюс команды отчёта о пересечениях и статистики для отчёта
курса.

## Technical Context

**Language/Version**: Python 3.12 (системный 3.12.3), `uv` 0.11.8, src-layout, сборка `uv_build`

**Primary Dependencies**: pydantic ≥ 2.12, typer ≥ 0.21, pyyaml, matplotlib; dev: pytest
(обоснование — research R6; сверено с context7)

**Storage**: файлы — `data/rumedbench/<commit>/…/*.jsonl` + `manifest.json` (вне git);
отчёты — `reports/data/*.{md,json,png}` (в git)

**Testing**: pytest, крошечные JSONL-фикстуры в `tests/fixtures/`, без сети (скачивание
тестируется через подмену источника на `file://`)

**Target Platform**: Linux-сервер (2 CPU, ~3 ГБ RAM), а также ноутбуки участников и Colab

**Project Type**: Python-библиотека + CLI (`uv run medbench …`)

**Performance Goals**: полная загрузка < 5 мин (SC-001), повторная < 10 с (SC-005);
весь корпус ≈ 13 МБ, грузится в память целиком

**Constraints**: без сети в тестах; без секретов; `data/` не коммитится; не зависеть от
наличия `data/MedBench_data`

**Scale/Scope**: 6 задач, 18 файлов, ≈ 35 тыс. примеров

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Как выполняется | Статус |
|---|---|---|
| I. Честная оценка | Роли `tune` = open dev, `final` = open test; `LeakageError` при пересечении; данные сайта не входят в роли; RuMedTest `final` недоступна | ✅ |
| II. Воспроизводимость | Коммит и sha256 всех файлов в `configs/data.yaml`; `manifest.json`; идемпотентная загрузка | ✅ |
| III. Сравнимость | Размеры сплитов сверяются со статьёй (SC-002); единые модели примеров для `preds.jsonl` в 002 | ✅ |
| IV. Визуализация | Холст «001 data-pipeline», ADR-012/013, обновлён «02 Data & Evaluation» | ✅ |
| V. Простота | 4 runtime-зависимости, stdlib для HTTP/хешей, без pandas/datasets | ✅ |
| VI. Тесты | pytest на загрузчик (file://), схемы, отпечатки, роли, отчёт пересечений; без сети | ✅ |

Повторная проверка после Phase 1: нарушений нет, Complexity Tracking не нужен.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-pipeline/
├── spec.md
├── plan.md              # этот файл
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/cli.md     # Phase 1: CLI и Python API
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml                 # uv, [project.scripts] medbench = "medbench.cli:app"
configs/
└── data.yaml                  # commit, файлы, sha256, rows, site_dir
src/medbench/
├── __init__.py
├── cli.py                     # корневое typer-приложение, add_typer(data_app, name="data")
└── data/
    ├── __init__.py            # публичный API: load_split, get_role, fingerprint, ошибки
    ├── schemas.py             # TaskName, SourceSplit, Role, *Example, Example (union)
    ├── config.py              # чтение configs/data.yaml
    ├── download.py            # скачивание + sha256 + manifest (urllib)
    ├── loaders.py             # JSONL → Example с номерами строк в ошибках
    ├── roles.py               # таблица ролей, проверка утечек
    ├── fingerprint.py         # нормализация и отпечатки
    ├── overlap.py             # отчёт сайт × open
    ├── stats.py               # статистика и гистограммы
    └── commands.py            # typer: download / verify / overlap / stats
reports/data/                  # overlap.md/json, stats.md/json, length_*.png
tests/
├── fixtures/                  # мини-JSONL по каждой задаче + битые строки
├── test_schemas.py
├── test_download.py           # file:// источник, sha256, идемпотентность
├── test_roles.py              # роли, RoleUnavailableError, LeakageError
├── test_fingerprint.py
└── test_overlap_stats.py
```

**Structure Decision**: единый Python-пакет `src/medbench` (src-layout, как в
`docs/ROADMAP.md`). Спека 001 создаёт каркас пакета, CLI и подпакет `data/`; следующие
спеки добавляют соседние подпакеты (`eval/`, `baselines/`, `llm/`).

## Post-design notes

- Спека обновлена по итогам research R2: данные сайта не входят в роль `train` (FR-005).
- `docs/ROADMAP.md` обновлён: роль подбора — open dev, у RuMedTest меток нет, добавлен холст
  001, статус 001 — 🟦.
- `.gitignore`: правило `data/` совпадало с любой папкой `data` (в т.ч. `src/medbench/data/`) — заменено на
  `/data/` (и `/context/`).
- **Реализация (ADR-014)**: в официальных сплитах есть точные дубликаты test в train/dev (NLI dev 2, NER
  train 28 / dev 7, SymptomRec train 1 строк — короткие шаблонные фразы). `final` остаётся официальным;
  дубликаты удаляются из `train`/`tune`, ожидаемые числа — `known_overlaps` в `configs/data.yaml`, любое
  другое число → `LeakageError`.

## Complexity Tracking

Нарушений конституции нет.
