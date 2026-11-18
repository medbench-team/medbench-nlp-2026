# Data Model: 002-eval-harness

## Prediction (строка `preds.jsonl`)

| Поле | Тип | Правила |
|---|---|---|
| `id` | str | id примера роли (`pairID`/`idx`), ровно один раз на пример |
| `prediction` | str \| list[str] \| int | NLI: `entailment\|contradiction\|neutral`; DaNet: `да\|нет`; RuMedTest: `1..4`; Top3/SymptomRec: список из **ровно 3** различных меток (первая — ответ для Acc); NER: список тегов длины = числу токенов, теги ∈ `O ∪ B-/I-{6 типов}` |
| `invalid` | bool = false | ответ модели не распознан, подставлена резервная метка (LLM) |
| `raw` | str \| null | сырой ответ, только при `invalid`, ≤ 500 символов |

Валидация (FR-003) — против `get_role(task, role)`: множество id совпадает (нет пропусков, лишних,
дублей); ошибка перечисляет до 20 проблемных id и их общее число.

## RunMeta (`meta.json`)

| Поле | Тип | Описание |
|---|---|---|
| `run_id` | str | `<YYYYMMDD-HHMMSS>_<approach>_<task>_<role>_<hash8>` |
| `approach` | str | `naive`, `tfidf`, `llm-zero-shot`, `rubioroberta-ft`, … (`[a-z0-9-]+`) |
| `model` | str | имя и тег модели (`gpt-oss:120b`, `-` для бейзлайнов) |
| `params` | dict | параметры подхода (промпт-версия, temperature, seed, …) |
| `config_hash` | str | sha256(canonical json {approach, model, params}) |
| `task`, `role` | TaskName, Role | роль ∈ {tune, final, submit} |
| `n_examples` | int | |
| `metrics` | dict[str, float] \| null | `{"acc": …, "hit3": …}` / `{"acc","f1"}`; `null` для `submit` |
| `invalid_rate` | float \| null | доля `invalid` (LLM) |
| `usage` | dict \| null | `{"input_tokens", "output_tokens", "latency_s_mean"}` |
| `code_commit` | str | `git rev-parse HEAD` (+ `-dirty`, если есть незакоммиченные изменения) |
| `data_commit` | str | `source.commit` из `configs/data.yaml` |
| `created_at` | str | ISO-8601 UTC |
| `justification` | str \| null | обязательно для повторного `final` той же `(config_hash, task)` |
| `notes` | str \| null | |

Проверка при загрузке прогона: `data_commit` ≠ текущему → `StaleRunError` (Edge Case
«старая версия данных»).

## TaskMetrics

`acc` (все задачи), `hit3` (Top3, SymptomRec), `f1` (NER); `score` — значение для Overall:
среднее двух метрик задачи или единственная метрика.

## PreviousArt (`configs/previous_art.yaml`)

```yaml
- system: RuBioRoBERTa
  source: "README sb-ai-lab/MedBench; arXiv:2204.03951"
  test: open            # open | site
  metrics:
    RuMedNLI: {acc: 82.77}
    RuMedDaNet: {acc: 76.17}
    RuMedTop3: {acc: 46.72, hit3: 72.87}
    RuMedSymptomRec: {acc: 44.01, hit3: 58.95}
    RuMedNER: {acc: 97.19, f1: 77.81}
  overall: 71.54
```

Записи: Naive, TF-IDF, BiLSTM, RuBERT, RuPoolBERT, RuBioBERT, RuBioRoBERTa, Человек (`open`);
ChatGPT (`site`: DaNet 89.3, NLI 61.3, RuMedTest 35.0). Ручные результаты сабмитов на сайт —
те же записи с `test: site`.

## Leaderboard (`results/leaderboard.md` + `.json`)

- Таблица **final** (open test): строки — подходы (последний `final`-прогон на
  `(config_hash, task)`), колонки — 5 задач + Overall; previous art `open` снизу; лучшая
  цифра по колонке выделена; строка «Δ к лучшему previous art» в п.п.
- Таблица **tune**: те же колонки, только наши прогоны.
- Таблица **site**: previous art `site` и ручные результаты сабмитов.
- Overall — только при наличии всех 5 задач у одной конфигурации (иначе «—»).

## Submission

`results/submissions/<YYYYMMDD-HHMMSS>.zip` с `RuMedDaNet.jsonl`, `RuMedNLI.jsonl`,
`RuMedTest.jsonl` в формате research R5; источник — указанные `run_id` роли `submit` или
последний `submit`-прогон по задаче. Проверка: все id `private_test` ровно по разу.
