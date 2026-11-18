---

description: "Task list for 003-baselines"
---

# Tasks: Бейзлайны — Naive и TF-IDF/CRF, воспроизведение статьи

**Input**: Design documents from `specs/003-baselines/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/baselines-cli.md,
quickstart.md; спеки 001 (`get_role`) и 002 (`save_run`, `score`, `leaderboard`, `submit`) реализованы

**Tests**: включены (конституция, принцип VI); без сети, на фикстурах `tests/conftest.py`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US3 из spec.md

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Добавить зависимости `uv add "scikit-learn>=1.9" "python-crfsuite>=0.9.12"` (`pyproject.toml`, `uv.lock`)
- [X] T002 Создать подпакет `src/medbench/baselines/` (`__init__.py`, `commands.py` с `baselines_app = typer.Typer(help="Baselines: naive and TF-IDF/CRF (paper reproduction).", no_args_is_help=True)`) и подключить в `src/medbench/cli.py` через `app.add_typer(baselines_app, name="baselines")`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: сами бейзлайны и раннер — общие для всех историй

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Реализовать в `src/medbench/baselines/base.py`: протокол `Baseline` (`approach: str`, `params: dict`, `fit(task, train)`, `predict(task, examples) -> list[Prediction]`, `supports(task) -> bool`) и `input_text(example)` — NLI: `premise + " " + hypothesis`, DaNet: `context + " " + question`, Top3/SymptomRec: `text` (как в `code/linear_models`, research.md R1)
- [X] T004 [P] Реализовать `NaiveBaseline` в `src/medbench/baselines/naive.py` по research.md R2: `approach="naive"`, `params={"strategy": "most_frequent", "ner": "token_lookup", "rumedtest": 1}`; NLI/DaNet — первая метка `Counter(train).most_common()` (даёт `entailment` / `да`); Top3/SymptomRec — 3 самых частых кода train («список из ровно 3 различных меток»); NER — самый частый тег каждого токена (с учётом регистра) в train, `O` для незнакомых; RuMedTest — `1` для каждого примера (`fit` не требуется, поддерживается только `submit`)
- [X] T005 [P] Реализовать `LinearBaseline` в `src/medbench/baselines/linear.py` по research.md R1, R3, R4: `approach="linear"`, общий `params={"tfidf": {"analyzer": "char", "ngram_range": [3, 8]}, "logreg": {"C": 10, "penalty": "l2", "scheme": "ovr", "max_iter": 1000}, "crf": {"algorithm": "lbfgs", "c1": 0.1, "c2": 0.01, "max_iterations": 200, "all_possible_transitions": true, "seed": 128}}`; текстовые задачи — `TfidfVectorizer(analyzer="char", ngram_range=(3, 8))` + `OneVsRestClassifier(LogisticRegression(C=10, max_iter=1000), n_jobs=2)`; NLI/DaNet — `predict`; Top3/SymptomRec — top-3 классов по убыванию `predict_proba`; NER — `pycrfsuite.Trainer` с признаками `word2features` из research.md R1, модель во временном файле (`tempfile`), `pycrfsuite.Tagger` для предсказания; `supports("RuMedTest") == False`
- [X] T006 Реализовать `run_baselines(approaches, tasks, roles, justification=None, config=None, results_dir=…)` в `src/medbench/baselines/runner.py` по data-model.md: обучение один раз на `get_role(task, "train")` → для каждой роли `predict(get_role(task, role))` → `medbench.eval.save_run(task, role, preds, approach=…, model="-", params=…)`; `RunOutcome(approach, task, role, status: saved|skipped, run_id|None, metrics|None, reason|None)`; пропуск (не ошибка): подход не поддерживает задачу, роль недоступна (`RoleUnavailableError`), `FinalRunExistsError` («финальный прогон уже есть — используйте --justification»); если ни одной роли нет для задачи — не обучать
- [X] T007 [P] Тесты `tests/test_baselines_naive.py` на фикстурах (`downloaded_config`): правила R2 (NLI → первая из равных частот, Top3 — ровно 3 различных кода в порядке частоты, NER-словарь с `O` для незнакомых, RuMedTest → `1`), предсказания проходят `validate_predictions` для `tune`
- [X] T008 [P] Тесты `tests/test_baselines_linear.py` на фикстурах: для каждой задачи кроме RuMedTest `fit` на train и `predict` на tune дают валидные предсказания (`validate_predictions`); Top3 — 3 различные метки; NER — длины равны числу токенов; `supports("RuMedTest") is False`; `params` одинаковы для всех задач
- [X] T009 Тесты `tests/test_baselines_runner.py` (results_dir во `tmp_path`): по умолчанию только `tune`; `final` сохраняется один раз, повторный запуск → `skipped` с причиной; `linear` + RuMedTest → `skipped`; `submit` для NER → `skipped`; все 5 задач одного подхода имеют одинаковый `config_hash`

**Checkpoint**: `run_baselines` работает на фикстурах

---

## Phase 3: User Story 1 — Воспроизвести бейзлайны статьи на финальном тесте (Priority: P1) 🎯 MVP

**Goal**: финальные прогоны naive и linear для 5 задач + отчёт о воспроизведении

**Independent Test**: `uv run medbench baselines run --role final` → `uv run medbench baselines report` — Naive ≤ 0.01 (кроме NER), linear ≤ 1 п.п. по всем метрикам и Overall

- [X] T010 [P] [US1] Тест `tests/test_baselines_report.py`: по синтетическим final-прогонам во `tmp_path` отчёт строит таблицу «наше / статья / Δ» для `Naive` и `TF-IDF + LogReg/CRF` из `configs/previous_art.yaml`, флаг допуска (naive ≤ 0.01 кроме NER, linear ≤ 1.0), Overall, раздел причин (ADR-014, ADR-018, sklearn/решатель); без final-прогонов → ошибка
- [X] T011 [US1] Реализовать `build_reproduction_report(results_dir)` и запись `reports/baselines/reproduction.{md,json}` в `src/medbench/baselines/report.py` (последний final-прогон на задачу для approach `naive`/`linear`, сопоставление с `system: "Naive"` и `system: "TF-IDF + LogReg/CRF"`)
- [X] T012 [US1] Добавить команды `run` (опции по contracts/baselines-cli.md: `--approach naive|linear|all`, повторяемые `--task`, `--role` с умолчанием `tune`, `--justification`; печать `approach task role → metrics | saved <run_id>` / `skip: <причина>`) и `report` в `src/medbench/baselines/commands.py`; экспорт API в `src/medbench/baselines/__init__.py`
- [X] T013 [US1] Запустить `uv run medbench baselines run --role final` на реальных данных (замерить время), затем `uv run medbench baselines report` и `uv run medbench eval leaderboard`; проверить SC-001, SC-002, SC-004; закоммитить-ready артефакты: `results/runs/*`, `reports/baselines/reproduction.md`, `results/leaderboard.md`

**Checkpoint**: бейзлайны статьи воспроизведены, в сводке есть Naive/linear с Overall

---

## Phase 4: User Story 2 — Метрики на «подборе» (Priority: P1)

**Goal**: прогоны на `tune` как нижняя планка для спек 004–007

**Independent Test**: `uv run medbench baselines run` (по умолчанию `tune`) → таблица «разработка» в `results/leaderboard.md`, без новых final

- [X] T014 [US2] Запустить `uv run medbench baselines run` на реальных данных; проверить, что созданы только `tune`-прогоны (10 шт.: naive × 5 + linear × 5), RuMedTest — `skip`; обновить `results/leaderboard.md`

**Checkpoint**: нижняя планка на dev доступна для сравнения

---

## Phase 5: User Story 3 — Первый сабмит на medbench.ru (Priority: P2)

**Goal**: submit-прогоны и архив для сайта

**Independent Test**: `uv run medbench eval submit --run <linear DaNet> --run <linear NLI> --run <naive RuMedTest>` → архив без предупреждений

- [X] T015 [US3] Запустить `uv run medbench baselines run --role submit` (linear: DaNet, NLI; naive: DaNet, NLI, RuMedTest); собрать сабмит из linear DaNet/NLI + naive RuMedTest через явные `--run`; проверить SC-005 (без предупреждений, 512/1536/397 строк); архив — в `results/submissions/` (вне git)

**Checkpoint**: первый сабмит готов к загрузке на сайт

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T016 [P] Обновить `README.md` (раздел «Бейзлайны»: команды, итоговая таблица из отчёта) и `CLAUDE.md` (команды `baselines run/report`)
- [X] T017 Пройти `specs/003-baselines/quickstart.md` (SC-003: сценарии 1, 2, 4 суммарно < 30 мин), `uv run pytest` без сети
- [ ] T018 Обновить Klyaksa-холст «003 baselines» итоговыми цифрами и расхождениями; после мержа — 003 зелёным на «00 Roadmap», ✅ в `docs/ROADMAP.md` и `context/PLAN.md`

---

## Dependencies & Execution Order

- Setup → Foundational (бейзлайны + раннер) → истории.
- **US1** (final + отчёт) и **US2** (tune) зависят только от Phase 2, независимы друг от друга.
- **US3** зависит от Phase 2 (и от US1/US2 не зависит).
- Polish — в конце.

### Parallel Opportunities

- Phase 2: T004 и T005 параллельно (разные файлы) после T003; тесты T007, T008 параллельно.
- После Phase 2: US1, US2, US3 можно запускать параллельно, но на сервере с 2 CPU и 3 ГБ RAM
  реальные прогоны лучше выполнять последовательно (пик 1.2 ГБ на процесс).

## Parallel Example: Phase 2

```bash
Task: "T004 NaiveBaseline в src/medbench/baselines/naive.py"
Task: "T005 LinearBaseline в src/medbench/baselines/linear.py"
```

## Implementation Strategy

### MVP First

1. Setup + Foundational → бейзлайны работают на фикстурах.
2. US1: финальный прогон + отчёт о воспроизведении — главный результат спеки.

### Incremental Delivery

1. US1 → строки Naive/linear в финальной сводке.
2. US2 → нижняя планка на dev для 004.
3. US3 → первый сабмит.

## Notes

- Реальные данные — только T013, T014, T015; тесты — на фикстурах без сети.
- `final` запускается ровно один раз (правило спеки 002); повтор — только с `--justification`.
