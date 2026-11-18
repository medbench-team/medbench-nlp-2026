# Research: 002-eval-harness

Дата: 2026-11-17. Источник формул — `code/eval.py` открытого репозитория `sb-ai-lab/MedBench @ dd57f4f`
(код прочитан, но не исполнялся). Предсказания моделей статьи (`code/{naive,linear_models,bilstm,bert,human}`)
скачаны как данные и пересчитаны собственным скриптом.

## R1. Формулы метрик (как в официальном скрипте)

| Задача | Метрики | Формула |
|---|---|---|
| RuMedNLI, RuMedDaNet | Acc | доля `prediction == gold` |
| RuMedTop3, RuMedSymptomRec | Acc, Hit@3 | Acc — по первой из трёх меток; Hit@3 — gold ∈ множество из трёх |
| RuMedNER | Acc, F1 | Acc — потокенная доля совпадений по всем токенам (seqeval `accuracy_score`); F1 — **micro**-F1 по сущностям (seqeval `f1_score` по умолчанию, нестрогий IOB-разбор `get_entities`) |
| Overall | — | среднее по 5 задачам; у Top3, SymptomRec, NER две метрики сначала усредняются |

Все значения ×100, вывод с двумя знаками.

- **Важно**: в `docs/ROADMAP.md` было «macro-F1» — неверно; официальный F1 для NER — micro по
  сущностям. ROADMAP исправлен.

## R2. Воспроизведение таблицы статьи (проверено)

| Набор (`code/…`) | Top3 | SymptomRec | DaNet | NLI | NER | Overall | Строка таблицы 3 |
|---|---|---|---|---|---|---|---|
| naive | 10.58/22.02 | 1.93/5.30 | 50.00 | 33.33 | 93.66/51.96 | 35.21 | Naive ✓ |
| linear_models | 49.76/72.75 | 32.05/49.40 | 51.95 | 59.70 | 94.40/62.89 | 58.46 | TF-IDF ✓ |
| bilstm | 40.88/63.50 | 20.24/31.33 | 52.34 | 60.06 | 94.74/63.26 | 53.87 | BiLSTM ✓ |
| bert | 47.45/70.44 | 34.94/52.05 | 71.48 | 77.29 | 96.47/73.15 | 67.20 | **RuPoolBERT** ✓ |
| human | 25.06/48.54 | 7.23/12.53 | 93.36 | 83.26 | 96.09/76.18 | 61.89 | Человек ✓ (Overall в статье не указан) |

Все предсказания покрывают официальный open test полностью (822 / 415 / 256 / 1422 / 693), у
Top3/SymptomRec ровно по 3 метки.

## R3. Реализация метрик: свои функции вместо seqeval/scikit-learn

- **Decision**: метрики реализуются в `medbench.eval.metrics` на чистом Python, включая разбор
  сущностей IOB, повторяющий нестрогую логику seqeval `get_entities` (сущность начинается на
  `B-`, на `I-` со сменой типа или после `O`; заканчивается на `O`, `B-` или смене типа).
  Корректность фиксируется: (а) юнит-тестами на ручных примерах и (б) командой
  `medbench eval paper`, которая скачивает (sha256 закреплены) предсказания моделей статьи и
  сверяет все числа с таблицей R2 до 0.01 (SC-001).
- **Rationale**: проверено, что собственная реализация F1 даёт ровно то же, что `seqeval`
  на всех пяти наборах. Принцип V: без `seqeval` + `numpy` + `scikit-learn` ради трёх формул;
  принцип III выполняется проверкой на официальных данных.
- **Alternatives considered**: зависимость `seqeval` (точно совпадает по построению, но тянет
  numpy/sklearn; sklearn всё равно понадобится в 003 — тогда можно добавить seqeval как
  dev-зависимость для перекрёстного теста, если понадобится).

## R4. Previous art: какой тест у какой цифры

| Источник | Тест | Цифры |
|---|---|---|
| Статья, таблица 3 | open test | Naive, TF-IDF, BiLSTM, RuBERT, RuPoolBERT, Человек |
| README репозитория (arXiv:2204.03951) | open test | RuBioBERT, **RuBioRoBERTa** (Top3 46.72/72.87, Rec 44.01/58.95, DaNet 76.17, NLI 82.77, NER 97.19/77.81, Overall 71.54) |
| `lb_submissions/SAI/ChatGPT` | **закрытый test сайта** | DaNet 89.3, NLI 61.3, RuMedTest 35.0 |

- **Decision**: в `configs/previous_art.yaml` у каждой записи поле `test: open | site`.
  SotA на open test сравнивается только с записями `open`; записи `site` показываются отдельной
  колонкой и сравниваются с нашими сабмитами на сайт (вносятся вручную).
- **Следствие**: на open test лучший опубликованный DaNet — **76.17** (RuBioRoBERTa), а не 89.3.
  ROADMAP исправлен (ADR-016).

## R5. Формат сабмита medbench.ru

Образец `lb_submissions/SAI/Naive/sample_submission.zip` (скачан и разобран):
`RuMedDaNet.jsonl` — `{"pairID", "answer": "да|нет"}`; `RuMedNLI.jsonl` — `{"pairID",
"gold_label"}`; `RuMedTest.jsonl` — `{"idx", "answer": "1".."4"}` (строка); `ECG2Pathology.jsonl`
— вне скоупа (ADR-007). Сабмиты ChatGPT/GigaChat в репозитории — тот же формат.

- **Decision**: `medbench eval submit` пишет zip ровно с этими именами и полями, порядок строк —
  как в `private_test`; без ECG.

## R6. Прогоны и правило «один final на конфигурацию»

- **Decision**: прогон — папка `results/runs/<run_id>/` с `preds.jsonl` и `meta.json`;
  `run_id = <YYYYMMDD-HHMMSS>_<approach>_<task>_<role>_<config_hash[:8]>`.
  `config_hash` — sha256 канонического JSON `{approach, model, params}` (без задачи, роли и
  данных). Правило I: при сохранении `final`-прогона ищется существующий `final` с тем же
  `(config_hash, task)`; найден → `FinalRunExistsError`, если не передано `--justification`.
- **Decision**: `results/runs/` коммитится целиком (preds ≤ ~1.5 тыс. строк на прогон, мало);
  сырые ответы LLM в `preds.jsonl` не пишутся (только `raw` до 500 символов для невалидных) —
  полный кеш ответов живёт в спеке 004 вне git.
- **Rationale**: принцип II — любые цифры воспроизводимы из `results/`.

## R7. Зависимости

- Новых runtime-зависимостей нет: `json`, `hashlib`, `zipfile`, `datetime`, `subprocess`
  (git-коммит) из stdlib; pydantic/typer/pyyaml уже есть.
