# Пересечения данных: сайт medbench.ru × открытый RuMedBench

Открытый репозиторий: `sb-ai-lab/MedBench @ dd57f4f`. Совпадение — по отпечатку нормализованных входных полей (NFC, нижний регистр, ё→е, пробелы).
Сгенерировано командой `uv run medbench data overlap`.

## Вывод

- **dev сайта = открытый test** → подбор моделей и промптов только на открытом dev (ADR-012).
- train сайта ≈ открытые train + dev; test сайта = открытый `private_test` → данные сайта в роли не входят, используются только для сверки (ADR-013).
- У RuMedTest меток нет ни в одном источнике: качество — только сабмитом на medbench.ru.

## RuMedNLI: сайт × open

| | open:train | open:dev | open:test | open:private_test |
|---|---|---|---|---|
| site:train | 11222 | 1395 | 2 | 0 |
| site:dev | 0 | 2 | 1421 | 0 |
| site:test | 0 | 0 | 0 | 1536 |

## RuMedDaNet: сайт × open

| | open:train | open:dev | open:test | open:private_test |
|---|---|---|---|---|
| site:train | 1052 | 256 | 0 | 0 |
| site:dev | 0 | 0 | 256 | 0 |
| site:test | 0 | 0 | 0 | 512 |

## RuMedTest: сайт × open

| | open:private_test |
|---|---|
| site:test | 397 |

## Побайтово идентичные файлы

- RuMedNLI: test сайта = open `private_test`
- RuMedDaNet: test сайта = open `private_test`
- RuMedTest: test сайта = open `private_test`

## Пересечения внутри открытых данных

Короткие шаблонные фразы; удаляются из ролей train/tune, test остаётся официальным (ADR-014, `known_overlaps` в `configs/data.yaml`).

- RuMedNLI: {"open:dev": {"open:test": 2}, "open:test": {"open:dev": 2}}
- RuMedDaNet: нет
- RuMedTest: нет
- RuMedNER: {"open:train": {"open:dev": 10, "open:test": 14}, "open:dev": {"open:train": 10, "open:test": 6}, "open:test": {"open:train": 14, "open:dev": 6}}
- RuMedTop3: нет
- RuMedSymptomRec: {"open:train": {"open:test": 1}, "open:test": {"open:train": 1}}

## Конфликты меток

- RuMedNER: open:train `2459114.tsv_8` = ['O', 'O', 'O', 'O', 'O'] vs open:test `2446305.tsv_15` = ['O', 'O', 'O', 'B-Drugform', 'I-Drugform']
- RuMedSymptomRec: open:train `q35695ed` = учащенное сердцебиение vs open:test `q4d4bdca` = дискомфорт в области шеи

## Дубликаты внутри сплитов

- RuMedNLI: open:train: 10, open:test: 1, site:train: 10, site:dev: 1
- RuMedDaNet: нет
- RuMedTest: нет
- RuMedNER: open:train: 51, open:dev: 3, open:test: 2
- RuMedTop3: open:train: 1
- RuMedSymptomRec: open:train: 6
