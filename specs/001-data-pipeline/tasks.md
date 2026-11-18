---

description: "Task list for 001-data-pipeline"
---

# Tasks: Данные RuMedBench — загрузка, канонические сплиты, EDA

**Input**: Design documents from `specs/001-data-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: включены — конституция (принцип VI) требует pytest на загрузчики и валидацию данных,
без сетевых вызовов.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4 из spec.md)
- Пути — от корня репозитория (single project, src-layout `src/medbench/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: каркас пакета `medbench` и окружение

- [X] T001 Инициализировать пакет через `uv init --package --name medbench --python 3.12 .` (не перезаписывая README.md) и привести `pyproject.toml` к виду: `requires-python = ">=3.12"`, сборка `uv_build` (нижняя граница — под установленный uv 0.11.x), `[project.scripts] medbench = "medbench.cli:app"`; удалить сгенерированный пример `main`, если появится
- [X] T002 Добавить зависимости `uv add "pydantic>=2.12" "typer>=0.21" pyyaml matplotlib` и `uv add --dev pytest`; `pyproject.toml` и `uv.lock` попадают в коммит
- [X] T003 [P] Создать корневое typer-приложение `app` с подкомандой-группой `data` (`app.add_typer(data_app, name="data")`, без команд пока) в `src/medbench/cli.py` и пустой `src/medbench/data/commands.py` с `data_app = typer.Typer(help="RuMedBench data")`
- [X] T004 [P] Настроить pytest (`[tool.pytest.ini_options] testpaths = ["tests"]`) в `pyproject.toml` и создать `tests/__init__.py`, `tests/conftest.py` с фикстурой `fixtures_dir`
- [X] T005 [P] Создать `reports/data/.gitkeep`; убедиться, что `data/` игнорируется (`git check-ignore data/rumedbench`), `reports/` — нет

**Checkpoint**: `uv sync && uv run medbench --help` показывает группу `data`; `uv run pytest` запускается (0 тестов)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: схемы, конфиг источника, чтение JSONL, отпечатки — нужны всем историям

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Реализовать перечисления `TaskName` (`RuMedNLI|RuMedDaNet|RuMedTest|RuMedNER|RuMedTop3|RuMedSymptomRec`), `SourceSplit` (`train|dev|test|private_test`), `Role` (`train|tune|final|submit`) и неизменяемые (`frozen=True`) pydantic-модели в `src/medbench/data/schemas.py` строго по data-model.md: общие поля `id: str`, `task`, `split`; `NLIExample(premise ← ru_sentence1, hypothesis ← ru_sentence2, label: entailment|contradiction|neutral | None)`; `DaNetExample(context, question, label: да|нет | None)`; `TestExample(question, options: tuple[str,str,str,str] ← "1".."4", label: 1..4 | None)` — «ровно 4 варианта»; `NERExample(tokens: tuple[str, ...], tags ← ner_tags)` — «`len(tags) == len(tokens)`, теги ∈ `O` ∪ `B-/I-{6 типов}`»; `ClassifExample(task ∈ {RuMedTop3, RuMedSymptomRec}, text ← symptoms, label ← code)`; «непустые тексты» во всех моделях; `Example = Annotated[Union[...], Field(discriminator="task")]`; функция `parse_raw(task, split, row: dict) -> Example`, переводящая исходные поля (`pairID`/`idx` → `id`) в модель
- [X] T007 [P] Определить исключения `DataError`, `DataNotFoundError`, `ChecksumError`, `SchemaError(task, file, line, detail)`, `RoleUnavailableError`, `LeakageError` в `src/medbench/data/errors.py` (сообщения на русском, с подсказкой `uv run medbench data download` для `DataNotFoundError`)
- [X] T008 Создать `configs/data.yaml` по формату data-model.md: `source.repo: sb-ai-lab/MedBench`, `source.commit: dd57f4f4f11aebe4fd18011b109d96b6d331a1bf`, `site_dir: data/MedBench_data`, `data_dir: data/rumedbench`, и 19 записей `files` (task, split, path `data/<Task>/<split>_v1.jsonl`, rows по research.md R3, sha256 — посчитать `sha256sum` по файлам, скачанным с этого коммита); и загрузчик `load_config(path) -> DataConfig` (pydantic) в `src/medbench/data/config.py`
- [X] T009 [P] Реализовать нормализацию и `fingerprint(example) -> str` в `src/medbench/data/fingerprint.py` по research.md R5: NFC → lower → `ё`→`е` → схлопывание пробелов → strip; SHA-1 от входных полей задачи (NLI: premise+hypothesis; DaNet: context+question; Test: question+options; NER: tokens через пробел; Top3/SymptomRec: text), метка не входит
- [X] T010 Реализовать `read_jsonl(path, task, split) -> list[Example]` в `src/medbench/data/loaders.py`: построчный разбор, пропуск пустых строк, `SchemaError` с задачей, файлом и номером строки при ошибке JSON/валидации; проверка уникальности `id` внутри файла; и `load_split(task, split, config=None) -> list[Example]` — чтение из `data/rumedbench/<commit>/`, `DataNotFoundError`, если файла нет (без сети)
- [X] T011 [P] Создать мини-фикстуры (по 3–6 строк) в `tests/fixtures/rumedbench/data/<Task>/<split>_v1.jsonl` для всех 6 задач и 19 сплитов из research.md R4 (с реальными именами полей), плюс `tests/fixtures/broken/` (нет поля, неверная метка NLI, NER с разной длиной токенов/тегов, дубль id)
- [X] T012 [P] Тесты схем и загрузчика в `tests/test_schemas.py`: корректный разбор каждой задачи, `label is None` для `private_test`, ошибки для каждого файла из `tests/fixtures/broken/` с номером строки в сообщении, неизменяемость моделей
- [X] T013 [P] Тесты отпечатков в `tests/test_fingerprint.py`: совпадение при разнице только в пробелах/регистре/ё, различие при разных текстах, независимость от метки

**Checkpoint**: `uv run pytest` зелёный; схемы и отпечатки готовы

---

## Phase 3: User Story 1 — Получить все данные одной командой (Priority: P1) 🎯 MVP

**Goal**: `uv run medbench data download` скачивает и проверяет 19 открытых файлов с коммита `dd57f4f`; `data verify` проверяет их без сети

**Independent Test**: на пустой `data/rumedbench` выполнить `uv run medbench data download` → таблица размеров совпадает с research.md R3; повторный запуск < 10 с без скачиваний; порча строки → `data verify` с кодом 1 и номером строки

### Tests for User Story 1

- [X] T014 [P] [US1] Тесты загрузчика в `tests/test_download.py`: источник подменяется на `file://` к `tests/fixtures/rumedbench` (base URL из конфига), sha256 фикстур считаются в тесте; проверяются скачивание всех файлов, запись `manifest.json`, идемпотентность (второй вызов ничего не скачивает), `ChecksumError` при неверном sha256, `--force` перекачивает
- [X] T015 [P] [US1] Тест CLI в `tests/test_cli_data.py` через `typer.testing.CliRunner`: `data download` на фикстурном конфиге → код 0 и таблица «задача × сплит»; `data verify` на испорченном файле → код 1, в выводе задача, файл, строка; отсутствие `site_dir` → предупреждение, код 0

### Implementation for User Story 1

- [X] T016 [US1] Реализовать `download_all(config, force=False) -> DownloadReport` в `src/medbench/data/download.py`: URL `{base_url}/{commit}/{path}` (base_url по умолчанию `https://raw.githubusercontent.com/sb-ai-lab/MedBench`, переопределяется в конфиге для тестов), `urllib.request` с таймаутом, запись во временный файл и атомарное переименование в `data/rumedbench/<commit>/<path>`, проверка sha256 и числа строк, пропуск уже проверенных файлов, `manifest.json` (sha256, rows, время)
- [X] T017 [US1] Реализовать `verify_all(config) -> VerifyReport` в `src/medbench/data/download.py`: без сети — наличие, sha256, число строк, полная валидация схемы через `read_jsonl`
- [X] T018 [US1] Добавить команды `download [--force] [--config]` и `verify [--config]` в `src/medbench/data/commands.py` по contracts/cli.md: таблица «задача × train/dev/test/private_test» (прочерк, если сплита нет), строка `site data: found/not found`, код 1 и понятное сообщение на `DataError`
- [X] T019 [US1] Экспортировать публичный API (`load_split`, `fingerprint`, модели, ошибки) в `src/medbench/data/__init__.py`
- [X] T020 [US1] Выполнить настоящую загрузку `uv run medbench data download` и сверить таблицу с research.md R3 (SC-002); замерить время первого и повторного запуска (SC-001, SC-005)

**Checkpoint**: US1 полностью работает — данные можно получить одной командой

---

## Phase 4: User Story 2 — Канонические сплиты без утечек (Priority: P1)

**Goal**: `get_role(task, role)` по таблице ролей data-model.md с проверкой утечек и отчёт о пересечениях сайт × open

**Independent Test**: `get_role('RuMedNLI','tune')` → 1395 примеров; `get_role('RuMedTest','final')` → `RoleUnavailableError`; `uv run medbench data overlap` → site dev ∩ open test = 1421 (NLI) и 256 (DaNet), site test = private_test

### Tests for User Story 2

- [X] T021 [P] [US2] Тесты ролей в `tests/test_roles.py` на фикстурах: соответствие таблице ролей data-model.md для всех 6 задач; `RoleUnavailableError` с текстом «RuMedTest: размеченных данных нет, доступна только роль submit» для train/tune/final RuMedTest и для `submit` у NER/Top3/SymptomRec; `LeakageError`, если в фикстуре пример из test продублирован в dev (через отдельный фикстурный конфиг)
- [X] T022 [P] [US2] Тесты отчёта о пересечениях в `tests/test_overlap.py`: фикстурная «версия сайта» в `tests/fixtures/site/` (train = open train+dev, dev = open test, test = private_test) → ожидаемая матрица; конфликт меток обнаруживается; без папки сайта — отчёт только по open + предупреждение

### Implementation for User Story 2

- [X] T023 [US2] Реализовать `get_role(task, role, config=None) -> list[Example]` в `src/medbench/data/roles.py`: таблица ролей ровно как в data-model.md (NLI/DaNet: train→train, tune→dev, final→test, submit→private_test; NER/Top3/SymptomRec: train/tune/final, submit недоступна; RuMedTest: только submit→private_test); перед выдачей `train`/`tune`/`final` проверка «отпечатки `final` не пересекаются с `train` и `tune`» → иначе `LeakageError` с числом совпадений (не фильтровать молча)
- [X] T024 [US2] Реализовать чтение версии сайта и `build_overlap_report(config) -> OverlapReport` в `src/medbench/data/overlap.py`: читать `site_dir/<Task>/{train,dev,test}.jsonl` для RuMedNLI, RuMedDaNet, RuMedTest через `parse_raw` (site split помечается отдельно, в роли не входит); матрица (сплит сайта × open train/dev/test/private_test) по отпечаткам, `label_conflicts`, `in_split_duplicates`; сохранение `reports/data/overlap.json` и `reports/data/overlap.md` (таблица + вывод «dev сайта = open test, подбор только на open dev»); ECG2Pathology игнорируется
- [X] T025 [US2] Добавить команду `overlap [--config]` в `src/medbench/data/commands.py`; экспортировать `get_role`, `Role` в `src/medbench/data/__init__.py`
- [X] T026 [US2] Запустить `uv run medbench data overlap` на реальных данных, сверить с таблицей research.md R2 (SC-004) и закоммитить `reports/data/overlap.{md,json}`

**Checkpoint**: US1 и US2 работают; следующие спеки могут брать данные через `get_role`

---

## Phase 5: User Story 3 — Статистика датасета для отчёта (Priority: P2)

**Goal**: `uv run medbench data stats` строит таблицы и графики для раздела Dataset

**Independent Test**: команда создаёт `reports/data/stats.md` с разделами для 6 задач и PNG-гистограммы длин; размеры совпадают со статьёй

### Tests for User Story 3

- [X] T027 [P] [US3] Тесты статистики в `tests/test_stats.py` на фикстурах: размеры сплитов, распределение меток, длины (min/median/p95/max в словах), наличие разделов всех задач в Markdown, PNG создаётся (backend `Agg`)

### Implementation for User Story 3

- [X] T028 [US3] Реализовать `build_stats(config) -> DatasetStats` в `src/medbench/data/stats.py` по data-model.md: по задаче и сплиту — число примеров, распределение меток (top-10 для Top3/SymptomRec, число классов), длины входов в словах, 1–2 примера; сравнение размеров с таблицей статьи (константы из research.md R3) с явным перечислением отличий
- [X] T029 [US3] Реализовать запись `reports/data/stats.md`, `reports/data/stats.json` и гистограмм `reports/data/length_<task>.png` (matplotlib, backend `Agg`) в `src/medbench/data/stats.py`
- [X] T030 [US3] Добавить команду `stats [--config]` в `src/medbench/data/commands.py`; запустить на реальных данных и закоммитить `reports/data/stats.{md,json}` и PNG (SC-006)

**Checkpoint**: материалы для раздела Dataset готовы

---

## Phase 6: User Story 4 — Расширенные задачи (Priority: P3)

**Goal**: RuMedNER, RuMedTop3, RuMedSymptomRec доступны в едином виде через `get_role`

**Independent Test**: `get_role('RuMedNER','train')` → 3440 примеров с `len(tags) == len(tokens)`; `get_role('RuMedTop3','final')` → 822 примера с непустыми `text` и `label`

- [X] T031 [US4] Добавить в `tests/test_roles.py` проверки расширенных задач на реальных данных под маркером `@pytest.mark.data` (пропуск, если данные не скачаны): размеры 3440/676/693, 4690/848/822, 2470/415/415, длины тегов NER, непустые коды Top3/SymptomRec; зарегистрировать маркер в `pyproject.toml`
- [X] T032 [US4] Проверить, что `stats.md` и `overlap.md` (US2, US3) включают расширенные задачи; при необходимости дополнить `src/medbench/data/stats.py`

**Checkpoint**: все 6 задач доступны через единый API

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T033 [P] Обновить `README.md`: установка (`uv sync`), загрузка данных, роли сплитов и предупреждение «dev сайта = open test», ссылка на `docs/ROADMAP.md`
- [X] T034 [P] Обновить раздел «Стек и команды» в `CLAUDE.md` реальными командами `uv run medbench data …`
- [X] T035 Пройти все сценарии `specs/001-data-pipeline/quickstart.md`, включая `uv run pytest` с отключённой сетью; отметить результаты в PR
- [ ] T036 Обновить Klyaksa: на холсте «001 data-pipeline» отразить отличия реализации от плана (если есть); после мержа — блок 001 на «00 Roadmap» зелёным, статус ✅ в `docs/ROADMAP.md` и `context/PLAN.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → истории.
- **US1 (Phase 3)** зависит только от Phase 2. MVP.
- **US2 (Phase 4)** зависит от Phase 2; для T026 (реальные данные) нужен T020 (US1).
- **US3 (Phase 5)** зависит от Phase 2; для T030 нужен T020.
- **US4 (Phase 6)** зависит от T023 (роли) и T030 (stats).
- **Polish** — после нужных историй.

### Within Each User Story

- Тесты пишутся первыми и падают до реализации.
- Модели/функции → команды CLI → прогон на реальных данных → коммит отчётов.

### Parallel Opportunities

- Phase 1: T003, T004, T005 параллельно после T001–T002.
- Phase 2: T007, T009, T011, T012, T013 параллельно (разные файлы); T008 и T010 — после T006.
- После Phase 2: US1, US2 (кроме T026) и US3 (кроме T030) можно делать параллельно.
- Внутри историй: тесты [P] параллельно друг с другом.

---

## Parallel Example: User Story 1

```bash
# Тесты US1 параллельно:
Task: "T014 [US1] Тесты загрузчика в tests/test_download.py"
Task: "T015 [US1] Тест CLI в tests/test_cli_data.py"
```

## Parallel Example: User Story 2

```bash
Task: "T021 [US2] Тесты ролей в tests/test_roles.py"
Task: "T022 [US2] Тесты отчёта о пересечениях в tests/test_overlap.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + Phase 2.
2. Phase 3 (US1) → проверить независимо: данные скачаны, проверены, таблица верна.
3. Сразу за ним US2 (тоже P1): без ролей следующие спеки рискуют утечкой.

### Incremental Delivery

1. Setup + Foundational → каркас пакета.
2. US1 → данные одной командой (MVP).
3. US2 → роли и отчёт о пересечениях — **разблокирует спеки 002–004**.
4. US3 → материалы для отчёта.
5. US4 → расширенные задачи для полного Overall.
6. Polish → README, CLAUDE.md, Klyaksa, PR в `dev`.

---

## Notes

- [P] tasks = different files, no dependencies
- Тесты не ходят в сеть (file:// фикстуры); реальные данные — только в T020, T026, T030, T031
- Коммит после каждой задачи или логической группы
- Останавливаться на checkpoint'ах для независимой проверки историй
