# Data Model: 003-baselines

## Baseline (интерфейс подхода)

| Поле/метод | Описание |
|---|---|
| `approach` | `naive` \| `linear` (строка `[a-z0-9-]+`, как в `RunMeta.approach`) |
| `params` | общий для всех задач словарь (research.md R6) → один `config_hash` → Overall в сводке |
| `fit(task, train: list[Example])` | обучение на роли `train` |
| `predict(task, examples) -> list[Prediction]` | предсказания в формате спеки 002 |

Ограничения предсказаний — как в `medbench.eval.predictions`: NLI/DaNet — одна метка;
Top3/SymptomRec — «список из ровно 3 различных меток» по убыванию уверенности; NER — «список
тегов длины = числу токенов»; RuMedTest — `1..4`.

| Задача | `naive` | `linear` |
|---|---|---|
| RuMedNLI | `most_common(train)[0]` → `entailment` | TF-IDF(char 3–8) на `premise + " " + hypothesis` + OvR LR(C=10) |
| RuMedDaNet | → `да` | TF-IDF на `context + " " + question` + OvR LR |
| RuMedTop3, RuMedSymptomRec | 3 самых частых кода | TF-IDF на `text` + OvR LR, top-3 по `predict_proba` |
| RuMedNER | самый частый тег токена (с учётом регистра), иначе `O` | CRF (R1) |
| RuMedTest | `1` (только `submit`) | — (нет train) → в сабмит идёт `naive` |

## BaselineRun (запуск)

`run_baselines(approaches, tasks, roles, justification=None)`:
для каждой пары (подход, задача): `fit` на `train` один раз → для каждой роли из `roles`
(`tune` по умолчанию; `final`, `submit` — явно) → `predict` → `medbench.eval.save_run`
(approach, model `-`, params, роль). Роль недоступна для задачи (например, `submit` у NER,
`linear` для RuMedTest) → пропуск с сообщением, не ошибка. `FinalRunExistsError` → сообщение
«финальный прогон уже есть» и продолжение остальных задач.

## ReproductionReport (`reports/baselines/reproduction.md` + `.json`)

Для `naive` и `linear` против записей `Naive` и `TF-IDF + LogReg/CRF` из
`configs/previous_art.yaml`: по каждой задаче/метрике — «наше / статья / Δ», признак «в
допуске» (Naive: ≤ 0.01, кроме NER; linear: ≤ 1.0), Overall, и раздел «Причины расхождений»
(ADR-014 — дубликаты test удалены из train NER/SymptomRec; ADR-018 — стратегия Naive NER;
версии sklearn/решателя). Источник цифр — последние `final`-прогоны в `results/runs/`.
