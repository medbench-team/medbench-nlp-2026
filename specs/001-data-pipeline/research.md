# Research: 001-data-pipeline

Дата: 2026-11-17. Все факты проверены скачиванием файлов, а не по документации.

## R1. Источник данных и фиксация версии

- **Decision**: единственный источник примеров — публичный репозиторий
  `github.com/sb-ai-lab/MedBench`, зафиксированный на коммите
  `dd57f4f4f11aebe4fd18011b109d96b6d331a1bf` (2026-02-02). Файлы скачиваются по
  `https://raw.githubusercontent.com/sb-ai-lab/MedBench/<sha>/data/<Task>/<split>_v1.jsonl`;
  SHA-256 каждого файла фиксируется в `configs/data.yaml` и проверяется после скачивания.
- **Rationale**: принцип II (воспроизводимость). Файлы маленькие (~13 МБ всего), клон
  репозитория не нужен.
- **Alternatives considered**: `git clone` (тянет `data/raw` на 10 МБ и код, нужен git на
  машине); HuggingFace-зеркала (неофициальные, версия не гарантирована).

## R2. Связь данных сайта с открытым репозиторием

Проверено попарным сравнением текстов и `cmp` файлов:

| Сплит сайта (`data/MedBench_data`) | Открытый репозиторий |
|---|---|
| RuMedNLI/train (12 627) | train 11 222 + dev 1 395 + 2 из test + 8 уникальных |
| RuMedNLI/dev (1 422) | test 1 421 (+ 1 уникальный) |
| RuMedDaNet/train (1 308) | train 1 052 + dev 256 |
| RuMedDaNet/dev (256) | test 256 |
| */test (NLI 1 536, DaNet 512, RuMedTest 397) | **побайтово** = `private_test_v1.jsonl` |

- **Decision**: данные сайта не являются отдельным источником примеров. Роли строятся только
  из открытого репозитория; `data/MedBench_data` (если есть) читается **только** для отчёта о
  пересечениях и для сверки, что `private_test` = test сайта. Уникальные примеры train сайта
  (≈10 у RuMedNLI) не добавляются в обучение.
- **Rationale**: всё нужное уже есть в открытых файлах; добавление 10 примеров не стоит
  сложности и риска утечки. Это упрощает FR-005 (обучение = open train).
- **Alternatives considered**: объединять train сайта с дедупликацией (как в спеке FR-005) —
  выигрыш 8–10 примеров из 11 232, отклонено (принцип V). Спека обновлена соответственно.

## R3. Наличие меток

| Задача | train | dev | test | private_test |
|---|---|---|---|---|
| RuMedNLI | 11 232 ✓ | 1 395 ✓ | 1 422 ✓ | 1 536 ✗ |
| RuMedDaNet | 1 052 ✓ | 256 ✓ | 256 ✓ | 512 ✗ |
| RuMedTest | — | — | — | 397 ✗ |
| RuMedNER | 3 440 ✓ | 676 ✓ | 693 ✓ | — |
| RuMedTop3 | 4 690 ✓ | 848 ✓ | 822 ✓ | — |
| RuMedSymptomRec | 2 470 ✓ | 415 ✓ | 415 ✓ | — |

Все размеры совпадают с таблицей 1 статьи RuMedBench. Классы NLI и DaNet идеально
сбалансированы во всех сплитах. Дубликатов идентификаторов внутри файлов нет.

- **Decision**: роли — `train` = open train, `tune` = open dev, `final` = open test,
  `submit` = private_test. Для RuMedTest доступна только роль `submit`; запрос других ролей —
  понятная ошибка (FR-008).

## R4. Поля и единая схема

| Задача | Поля исходника | Метка |
|---|---|---|
| RuMedNLI | `pairID`, `ru_sentence1`, `ru_sentence2` | `gold_label` ∈ {entailment, contradiction, neutral} |
| RuMedDaNet | `pairID`, `context`, `question` | `answer` ∈ {да, нет} |
| RuMedTest | `idx`, `question`, `"1"`…`"4"` | нет (ответ ∈ {1, 2, 3, 4}) |
| RuMedNER | `idx`, `tokens` | `ner_tags` (IOB, 6 типов), длина = `tokens` |
| RuMedTop3 | `idx`, `symptoms` | `code` (МКБ-10, 105 классов в train) |
| RuMedSymptomRec | `idx`, `symptoms` | `code` (симптом, 141 класс в train) |

- **Decision**: дискриминированное объединение pydantic v2 по полю `task`
  (`Field(discriminator="task")`, сверено с context7 `/pydantic/pydantic/v2.12.5`); общие поля
  `id`, `task`, `split`; модели неизменяемые (`frozen=True`).
- **Rationale**: одна точка валидации (FR-003), понятные ошибки с путём к полю.

## R5. Нормализация для поиска пересечений

- **Decision**: отпечаток = SHA-1 от нормализованных входных полей задачи; нормализация:
  Unicode NFC → нижний регистр → `ё`→`е` → схлопывание пробельных символов → обрезка.
  Поля: NLI — (посылка, гипотеза); DaNet — (контекст, вопрос); RuMedTest — (вопрос, варианты);
  NER — токены через пробел; Top3/SymptomRec — текст жалоб.
- **Rationale**: ловит совпадения, отличающиеся только пробелами/регистром (Edge Cases).
- **Alternatives considered**: MinHash/near-duplicates — вне скоупа спеки.

## R6. Зависимости и стек (сверено с context7)

- **Decision**: `pydantic>=2.12`, `typer>=0.21` (подкоманды через `app.add_typer(..., name=...)`,
  точка входа `[project.scripts] medbench = "medbench.cli:app"`), `pyyaml` (конфиги YAML —
  принцип II), `matplotlib` (гистограммы для отчёта); dev: `pytest`. Скачивание — stdlib
  `urllib.request` + `hashlib`. Сборка — `uv_build`, src-layout (`uv init --package`).
- **Rationale**: принцип V — без `requests`/`httpx`, без `pandas` (статистика считается
  простыми счётчиками, таблицы пишутся в Markdown/CSV).
- **Alternatives considered**: `datasets` (HF) — тяжёлая зависимость ради 13 МБ JSONL;
  `pandas` — удобно для EDA, но не нужно для фиксированного набора таблиц.

## R8. Дубликаты test внутри официальных сплитов (найдено при реализации)

- Факт: RuMedNLI test ∩ dev = 2 (пары «Диабет 2 типа.» + гипотеза), RuMedNER test ∩ train = 14 и
  ∩ dev = 6 отпечатков (28 и 7 строк: «Время использования : 1 месяц», «Рекомендую .»),
  RuMedSymptomRec test ∩ train = 1 (одинаковый текст, **разные** метки). Конфликты меток — в
  `reports/data/overlap.md`.
- **Decision** (ADR-014): `final` = официальный test без изменений (сравнимость с previous art);
  дубликаты удаляются из `train`/`tune`; ожидаемое число строк — `known_overlaps` в
  `configs/data.yaml`, иначе `LeakageError`.
- **Alternatives**: удалять из test (ломает сравнимость); ничего не делать (утечка в подбор).

## R7. Окружение

- Python 3.12.3 в системе, `uv 0.11.8`. Ограничение `requires-python = ">=3.12"`.
  Нижнюю границу `uv_build` выставить под установленный uv при `uv init`.
- Сервер: 2 CPU, ~3 ГБ RAM — данные (≈13 МБ) целиком помещаются в память.
