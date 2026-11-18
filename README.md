# medbench-nlp-2026

Russian medical NLP: RuMedBench (RuMedNLI, RuMedDaNet, RuMedTest). ITMO AI Talent Hub NLP course
project, Autumn 2026.

Цель — SotA на русскоязычном медицинском бенчмарке RuMedBench с честным сравнением с
опубликованными результатами. План и статусы — [`docs/ROADMAP.md`](docs/ROADMAP.md), правила —
[`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Установка

```bash
uv sync                      # Python 3.12 + зависимости
uv run pytest                # тесты (без сети)
```

## Данные

```bash
uv run medbench data download   # открытый RuMedBench @ dd57f4f, проверка sha256 и схемы (~10 с)
uv run medbench data verify     # офлайн-проверка скачанных файлов
uv run medbench data overlap    # отчёт о пересечениях с версией сайта → reports/data/overlap.md
uv run medbench data stats      # статистика для отчёта → reports/data/stats.md
```

Файлы ложатся в `data/rumedbench/<commit>/` (не в git). Источник и контрольные суммы —
[`configs/data.yaml`](configs/data.yaml).

В коде данные берутся **по ролям**, а не по файлам:

```python
from medbench.data import get_role

train = get_role("RuMedNLI", "train")   # обучение: open train
tune = get_role("RuMedNLI", "tune")     # подбор моделей и промптов: open dev
final = get_role("RuMedNLI", "final")   # один финальный прогон: open test (сравнение с previous art)
submit = get_role("RuMedTest", "submit")  # закрытый test → сабмит на medbench.ru
```

> ⚠️ **dev с сайта medbench.ru — это открытый test.** Подбирать что-либо на нём нельзя.
> Версия сайта (`data/MedBench_data/`) используется только для сверки
> ([`reports/data/overlap.md`](reports/data/overlap.md)). У RuMedTest меток нет нигде — только
> сабмит. Несколько официальных дубликатов test в train/dev удаляются из ролей `train`/`tune`
> (`known_overlaps` в конфиге), test остаётся официальным.

## Оценка

```bash
uv run medbench eval paper                         # сверка наших метрик с таблицей 3 статьи (до 0.01)
uv run medbench eval score preds.jsonl --task RuMedNLI --role tune   # метрики без сохранения
uv run medbench eval save preds.jsonl --task RuMedNLI --role tune --approach tfidf --model -
uv run medbench eval rescore results/runs/<run_id>  # пересчёт сохранённого прогона
uv run medbench eval leaderboard                   # results/leaderboard.md: наши прогоны vs previous art
uv run medbench eval submit                        # zip для medbench.ru (DaNet, NLI, RuMedTest)
```

Метрики повторяют официальный `code/eval.py` (Acc, Hit@3, NER — потокенная Acc и micro-F1 по
сущностям, Overall по 5 задачам). Любой подход сохраняет результаты только через
`medbench.eval.save_run` → `results/runs/<run_id>/{preds.jsonl, meta.json}`.

> ⚠️ **Один final на конфигурацию.** Повторный прогон на роли `final` с теми же
> approach/model/params отклоняется; повтор — только с `--justification`, которое попадает в
> сводку. Previous art на открытом test и на закрытом test сайта сравниваются раздельно
> (DaNet open SotA = 76.17, а не 89.3 ChatGPT — та цифра с сайта).

## Бейзлайны (спека 003)

```bash
uv run medbench baselines run                 # роль tune (по умолчанию): нижняя планка на dev
uv run medbench baselines run --role final    # один финальный прогон (повтор — только с --justification)
uv run medbench baselines run --role submit   # предсказания для закрытого теста сайта
uv run medbench baselines report              # reports/baselines/reproduction.md
```

Воспроизведение статьи на открытом test (≈ 7 мин на роль, пик ~1 ГБ RAM):

| | Top3 | SymptomRec | DaNet | NLI | NER | Overall |
|---|---|---|---|---|---|---|
| naive (наш) | 10.58 / 22.02 | 1.93 / 5.30 | 50.00 | 33.33 | 94.31 / 54.24 | 35.50 |
| Naive (статья) | 10.58 / 22.02 | 1.93 / 5.30 | 50.00 | 33.33 | 93.66 / 51.96 | 35.21 |
| TF-IDF/CRF (наш) | 49.51 / 71.90 | 30.36 / 48.67 | 51.95 | 59.56 | 94.28 / 62.12 | 57.99 |
| TF-IDF/CRF (статья) | 49.76 / 72.75 | 32.05 / 49.40 | 51.95 | 59.70 | 94.40 / 62.89 | 58.46 |

14 из 15 метрик в допуске; вне допуска — SymptomRec Acc (−1.69 п.п.), причины — в
[`reports/baselines/reproduction.md`](reports/baselines/reproduction.md).

## Потолок LLM (спека 004)

Zero-shot через Ollama Cloud: LangChain `ChatOllama` и граф LangGraph (промпт → кеш → вызов → парсер →
повтор или резервная метка). Ключ `OLLAMA_API_KEY` читается только из `.env`. Ответы кешируются в
`data/llm_cache/`, поэтому повторный запуск ничего не стоит.

```bash
uv run medbench llm models                          # каталог облака и проверка моделей из configs/llm_ceiling.yaml
uv run medbench llm run --limit 20                  # пробный прогон, ничего не сохраняет
uv run medbench llm run                             # tune: 4 модели × NLI, DaNet (≈ 2.2 ч без кеша)
uv run medbench llm run --model glm-5.3 --role final
uv run medbench llm run --model glm-5.3 --task RuMedTest --task RuMedNLI --task RuMedDaNet --role submit
uv run medbench llm report                          # reports/llm/ceiling.{md,json}
```

Открытый dev (`tune`), Acc в %, невалидных ответов 0% у всех моделей:

| Модель | RuMedNLI | RuMedDaNet |
|---|---|---|
| glm-5.3 | **86.00** | **96.88** |
| gemma4:31b | 85.00 | 96.48 |
| gpt-oss:120b | 82.05 | 95.31 |
| deepseek-v4-pro:0813 | 78.82 | 94.92 |
| TF-IDF (бейзлайн) | 61.67 | 51.56 |

В финал выбраны glm-5.3 и gemma4:31b, только по tune (обоснование — `specs/004-llm-ceiling-ollama/research.md`, R9).
Открытый test (`final`, один прогон на конфигурацию):

| Модель | RuMedNLI | RuMedDaNet |
|---|---|---|
| glm-5.3 | **86.99** | 98.44 |
| gemma4:31b | 85.51 | **98.83** |
| previous art (RuBioRoBERTa) | 82.77 | 76.17 |

Полная сводка — [`results/leaderboard.md`](results/leaderboard.md).
