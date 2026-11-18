---

description: "Task list for 002-eval-harness"
---

# Tasks: Харнесс оценки — метрики как в статье, реестр прогонов, сабмит

**Input**: Design documents from `specs/002-eval-harness/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/eval-api.md, quickstart.md;
спека 001 (`medbench.data.get_role`) реализована

**Tests**: включены — конституция (принцип VI) требует pytest на метрики; тесты без сети.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 из spec.md
- Пути — от корня репозитория

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: каркас `medbench.eval`, конфиги previous art и предсказаний статьи

- [X] T001 Создать подпакет `src/medbench/eval/` (`__init__.py`, пустой `commands.py` с `eval_app = typer.Typer(help="Evaluation: metrics, runs, leaderboard, submission.", no_args_is_help=True)`) и подключить его в `src/medbench/cli.py` через `app.add_typer(eval_app, name="eval")`
- [X] T002 [P] Создать `configs/previous_art.yaml` по data-model.md (список записей `system`, `source`, `test: open|site`, `metrics` по задачам, `overall`): open — Naive, TF-IDF, BiLSTM, RuBERT (Top3 39.54/62.29, Rec 18.55/34.22, DaNet 67.19, NLI 77.64, NER 96.63/73.53, Overall 61.44), RuPoolBERT, RuBioBERT (43.55/68.86, 28.94/44.55, 53.91, 80.31, 96.63/75.97, 62.69), RuBioRoBERTa (46.72/72.87, 44.01/58.95, 76.17, 82.77, 97.19/77.81, 71.54), Человек (25.06/48.54, 7.23/12.53, 93.36, 83.26, 96.09/76.18, overall 61.89 — «пересчитано нами»); site — ChatGPT text-davinci-003 (DaNet 89.3, NLI 61.3, RuMedTest 35.0); остальные цифры open — из research.md R2
- [X] T003 [P] Создать `configs/paper_outputs.yaml`: `commit: dd57f4f4f11aebe4fd18011b109d96b6d331a1bf`, `base_url`, 25 файлов (наборы `naive`, `linear_models`, `bilstm`, `bert`, `human` × задачи `RuMedTop3`, `RuMedSymptomRec`, `RuMedDaNet`, `RuMedNLI`, `RuMedNER`; путь `code/<set>/out/<Task>.jsonl`, для `naive`/`human` — `code/<set>/<Task>.jsonl`) с sha256, посчитанными по файлам этого коммита, и ожидаемые метрики каждого набора из research.md R2 (`bert` помечен как «RuPoolBERT»)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: модель предсказания, чтение/запись `preds.jsonl`, валидация против роли — нужны US1, US2, US4

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Определить исключения `EvalError`, `PredictionError(task, problems: list[str], total: int)`, `EvalUnavailableError`, `FinalRunExistsError`, `StaleRunError` в `src/medbench/eval/errors.py` (сообщения на русском; `PredictionError` показывает до 20 проблем и общее число)
- [X] T005 Реализовать `Prediction` (pydantic, `frozen=True`, `extra="forbid"`: `id: str`, `prediction: str | int | list[str]`, `invalid: bool = False`, `raw: str | None` — «только при `invalid`, ≤ 500 символов») и `read_predictions(path)`, `write_predictions(path, preds)` в `src/medbench/eval/predictions.py`
- [X] T006 Реализовать `validate_predictions(task, role, preds, config=None) -> dict[str, Prediction]` в `src/medbench/eval/predictions.py` против `medbench.data.get_role(task, role)`: «множество id совпадает (нет пропусков, лишних, дублей)»; значения: NLI `entailment|contradiction|neutral`, DaNet `да|нет`, RuMedTest `1..4` (int или строка-цифра), Top3/SymptomRec — «список из ровно 3 различных меток», NER — «список тегов длины = числу токенов, теги ∈ `O ∪ B-/I-{6 типов}`» (`medbench.data.schemas.NER_TAGS`); все нарушения собираются в один `PredictionError`
- [X] T007 [P] Тесты в `tests/test_predictions.py` на фикстурном конфиге из `tests/conftest.py` (`downloaded_config`): корректные предсказания проходят; пропуск, лишний id, дубль, неверная метка NLI, Top3 из 2 меток и с дублем, NER неверной длины и с неизвестным тегом → `PredictionError` с id; чтение/запись `preds.jsonl` туда-обратно

**Checkpoint**: предсказания валидируются против ролей спеки 001

---

## Phase 3: User Story 1 — Метрики ровно как в статье (Priority: P1) 🎯 MVP

**Goal**: `score()` и `uv run medbench eval score` дают числа официального `code/eval.py`; `uv run medbench eval paper` воспроизводит таблицу 3

**Independent Test**: `uv run medbench eval paper` → все 5 наборов совпадают с research.md R2 (≤ 0.01), код 0

### Tests for User Story 1

- [X] T008 [P] [US1] Тесты формул в `tests/test_metrics.py`: accuracy и hit@3 на ручных примерах; IOB-разбор `ner_entities` на случаях seqeval-нестрогого режима (`B-X I-X`, одиночный `I-X` после `O` — начало сущности, `I-Y` после `B-X` — новая сущность, сущность в конце последовательности, смежные `B-X B-X`); micro-F1 (tp/fp/fn по сущностям всех предложений); потокенная Acc; `overall` = среднее 5 задач с предварительным усреднением двух метрик, `None` при неполном наборе; округление не применяется внутри (только при выводе)
- [X] T009 [P] [US1] Тест `tests/test_paper.py` с `@pytest.mark.data` (skip без сети/данных): скачать по `configs/paper_outputs.yaml` и сверить все метрики 5 наборов с ожидаемыми ≤ 0.01; плюс офлайн-тест разбора формата официальных файлов (`code`/`prediction`, `answer`/`gold_label`/`ner_tags` + `prediction`) на 2–3 строках-фикстурах `tests/fixtures/paper/`

### Implementation for User Story 1

- [X] T010 [US1] Реализовать в `src/medbench/eval/metrics.py`: `accuracy(gold, pred)`, `hit_at_3(gold, top3)`, `ner_entities(tags) -> set[(type, start, end)]` (нестрогий IOB как seqeval `get_entities`, research.md R3), `ner_token_accuracy`, `ner_f1` (micro по сущностям), `TaskMetrics` (`acc`, `hit3 | None`, `f1 | None`, свойство `score` — среднее двух или одна), `overall(per_task)`; всё в процентах, без округления
- [X] T011 [US1] Реализовать `score(task, predictions, role, config=None) -> TaskMetrics` в `src/medbench/eval/__init__.py` (или `scoring.py`): `EvalUnavailableError` для RuMedTest и ролей `submit`/`train`; валидация T006; gold из `get_role`
- [X] T012 [US1] Реализовать `src/medbench/eval/paper.py`: загрузка `configs/paper_outputs.yaml`, скачивание с sha256 в `data/paper_outputs/<commit>/` (переиспользовать `_fetch`/`_sha256` из `src/medbench/data/download.py`, вынеся их в общий `src/medbench/data/download.py` API), расчёт метрик по полям официального формата через функции T010, сравнение с ожидаемыми, таблица результата
- [X] T013 [US1] Добавить команды `score <preds.jsonl> --task --role` и `paper` в `src/medbench/eval/commands.py` по contracts/eval-api.md (вывод метрик с двумя знаками; код 1 и список id при `PredictionError`)
- [X] T014 [US1] Запустить `uv run medbench eval paper` на реальных файлах и сверить с research.md R2 (SC-001)

**Checkpoint**: метрики совпадают с официальными

---

## Phase 4: User Story 2 — Единый формат и реестр прогонов (Priority: P1)

**Goal**: `save_run` / `load_run` / `eval save` / `eval rescore`; правило «один final на (config_hash, task)»

**Independent Test**: сохранить прогон на `tune`, пересчитать `eval rescore` → совпадает; второй `final` той же конфигурации без `--justification` → код 1

### Tests for User Story 2

- [X] T015 [P] [US2] Тесты в `tests/test_runs.py` (results_dir во `tmp_path`): `config_hash` не зависит от порядка ключей `params` и от задачи/роли; `save_run` создаёт `preds.jsonl` + `meta.json` со всеми полями data-model.md; `metrics = null` для `submit`; `invalid_rate` считается; повторный `final` той же `(config_hash, task)` → `FinalRunExistsError`, с `justification` — сохраняется; `load_run` с чужим `data_commit` → `StaleRunError`; `rescore` совпадает с `meta.json`

### Implementation for User Story 2

- [X] T016 [US2] Реализовать в `src/medbench/eval/runs.py`: `RunMeta` (pydantic, поля data-model.md: `run_id`, `approach` — «`[a-z0-9-]+`», `model`, `params`, `config_hash`, `task`, `role` ∈ {tune, final, submit}, `n_examples`, `metrics`, `invalid_rate`, `usage`, `code_commit`, `data_commit`, `created_at`, `justification`, `notes`); `config_hash(approach, model, params)` — sha256 канонического JSON (`sort_keys=True`, `ensure_ascii=False`, без пробелов); `code_commit()` через `git rev-parse HEAD` + `-dirty` при `git status --porcelain` (fallback `unknown`); `run_id` = `<YYYYMMDD-HHMMSS>_<approach>_<task>_<role>_<hash8>`; `RESULTS_DIR = Path("results")` с переопределением аргументом
- [X] T017 [US2] Реализовать `save_run(...)`, `load_run(run_dir)`, `list_runs(results_dir)`, `rescore(run_dir)` в `src/medbench/eval/runs.py`: валидация T006, метрики T011 (кроме `submit`), правило final с `justification`, проверка `data_commit` при загрузке; экспорт в `src/medbench/eval/__init__.py`
- [X] T018 [US2] Добавить команды `save` (опции по contracts/eval-api.md, `--params` — путь к JSON) и `rescore` в `src/medbench/eval/commands.py`; создать `results/runs/.gitkeep`, добавить `results/submissions/` в `.gitignore`

**Checkpoint**: подходы 003–009 могут сохранять результаты

---

## Phase 5: User Story 3 — Сводная таблица против previous art (Priority: P2)

**Goal**: `uv run medbench eval leaderboard` → `results/leaderboard.{md,json}`

**Independent Test**: на 3–4 сохранённых прогонах (tune и final, неполный набор задач) сводка показывает отдельные таблицы, previous art open/site, Δ, Overall «—» для неполных

### Tests for User Story 3

- [X] T019 [P] [US3] Тесты в `tests/test_leaderboard.py` (прогоны во `tmp_path`): final и tune в разных таблицах; для повторных final берётся последний и помечается обоснование; Overall только при 5/5 задачах; лучшая цифра колонки выделена; Δ к лучшему previous art `open`; записи `site` — отдельная таблица; previous_art.yaml валидируется (неизвестная задача/метрика → ошибка)

### Implementation for User Story 3

- [X] T020 [US3] Реализовать `src/medbench/eval/leaderboard.py`: загрузка/валидация `configs/previous_art.yaml`, `build_leaderboard(results_dir)` (группировка по `(approach, model, config_hash)`), рендер Markdown (три таблицы, жирным — лучшее в колонке, строка «лучший previous art (open)», Δ в п.п. со знаком) и JSON
- [X] T021 [US3] Добавить команду `leaderboard` в `src/medbench/eval/commands.py`; сгенерировать `results/leaderboard.md` (пока только previous art) и проверить время на 100 синтетических прогонах < 10 с (SC-003)

**Checkpoint**: сводка для раздела результатов готова

---

## Phase 6: User Story 4 — Сабмит на medbench.ru (Priority: P2)

**Goal**: `uv run medbench eval submit` → zip в формате `sample_submission.zip`

**Independent Test**: наивные `submit`-прогоны для DaNet/NLI/RuMedTest во `tmp_path` → zip с тремя файлами, 512/1536/397 строк, поля как в образце

### Tests for User Story 4

- [X] T022 [P] [US4] Тесты в `tests/test_submission.py` (фикстурный конфиг): имена файлов `RuMedDaNet.jsonl` / `RuMedNLI.jsonl` / `RuMedTest.jsonl`; поля `{"pairID","answer"}`, `{"pairID","gold_label"}`, `{"idx","answer": "1".."4" строкой}`; порядок строк как в `private_test`; нет прогона для задачи → предупреждение и архив без неё; `naive_fill=True` → наивный ответ (`да`, `neutral`, `"1"`, как в `lb_submissions/SAI/Naive`); явные `run_ids` не роли `submit` → ошибка

### Implementation for User Story 4

- [X] T023 [US4] Реализовать `build_submission(run_ids=None, naive_fill=False, results_dir=…, out_dir=results/submissions)` в `src/medbench/eval/submission.py`: выбор последних `submit`-прогонов по задачам или явных, преобразование в формат research.md R5, проверка «все id `private_test` ровно по разу», запись zip `<YYYYMMDD-HHMMSS>.zip`
- [X] T024 [US4] Добавить команду `submit [--run RUN_ID ...] [--naive-fill]` в `src/medbench/eval/commands.py`; собрать наивный архив во временную папку и сравнить структуру с `sample_submission.zip` из официального репозитория (SC-004)

**Checkpoint**: все истории готовы

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T025 [P] Обновить `README.md` (раздел «Оценка»: `eval paper`, `save`, `leaderboard`, `submit`; правило одного final) и `CLAUDE.md` («результаты сохранять только через `medbench.eval.save_run`»)
- [X] T026 Пройти сценарии `specs/002-eval-harness/quickstart.md`, `uv run pytest` без сети (`unshare -rn`)
- [ ] T027 Обновить Klyaksa-холст «002 eval-harness» по фактической реализации; после мержа — 002 зелёным на «00 Roadmap», ✅ в `docs/ROADMAP.md` и `context/PLAN.md`

---

## Dependencies & Execution Order

- Setup → Foundational → истории.
- **US1** зависит от Phase 2. MVP.
- **US2** зависит от Phase 2 и `score` из US1 (T011).
- **US3** зависит от US2 (прогоны).
- **US4** зависит от US2 (submit-прогоны).
- Polish — в конце.

### Parallel Opportunities

- Phase 1: T002, T003 параллельно после T001.
- Phase 2: T007 параллельно с реализацией после T005.
- Тесты внутри историй ([P]) параллельно; US3 и US4 параллельно после US2.

## Parallel Example: User Story 1

```bash
Task: "T008 [US1] Тесты формул в tests/test_metrics.py"
Task: "T009 [US1] Тест tests/test_paper.py"
```

## Parallel Example: после US2

```bash
Task: "T019 [US3] Тесты в tests/test_leaderboard.py"
Task: "T022 [US4] Тесты в tests/test_submission.py"
```

## Implementation Strategy

### MVP First

1. Setup + Foundational.
2. US1 → `eval paper` совпадает со статьёй — харнесс доказанно корректен.
3. US2 сразу следом: без реестра спеки 003–004 не смогут сохранять результаты.

### Incremental Delivery

1. US1 (метрики) → US2 (прогоны) — **разблокирует 003 и 004**.
2. US3 (сводка) → материалы для отчёта.
3. US4 (сабмит) → RuMedTest и лидерборд.

## Notes

- Тесты без сети; реальные данные/скачивание — только T009 (`data`), T014, T024.
- Коммит после каждой логической группы.
