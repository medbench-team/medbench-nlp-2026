# Data Model: 001-data-pipeline

## Перечисления

- `TaskName`: `RuMedNLI` | `RuMedDaNet` | `RuMedTest` | `RuMedNER` | `RuMedTop3` |
  `RuMedSymptomRec`
- `SourceSplit` (файл в репозитории): `train` | `dev` | `test` | `private_test`
- `Role` (как используем): `train` | `tune` | `final` | `submit`

## Example (дискриминированное объединение по `task`)

Общие поля (у всех): `id: str` (из `pairID`/`idx`), `task: TaskName`, `split: SourceSplit`.
Все модели неизменяемые. Метка `None` только для `private_test`.

| Модель | `task` | Входные поля | Метка | Валидация |
|---|---|---|---|---|
| `NLIExample` | RuMedNLI | `premise` ← `ru_sentence1`, `hypothesis` ← `ru_sentence2` | `label: entailment\|contradiction\|neutral \| None` | непустые тексты |
| `DaNetExample` | RuMedDaNet | `context`, `question` | `label: да\|нет \| None` | непустые тексты |
| `TestExample` | RuMedTest | `question`, `options: tuple[str,str,str,str]` ← `"1"`…`"4"` | `label: 1..4 \| None` (всегда `None` в текущих данных) | ровно 4 варианта |
| `NERExample` | RuMedNER | `tokens: tuple[str, ...]` | `tags: tuple[str, ...]` ← `ner_tags` | `len(tags) == len(tokens)`, теги ∈ `O` ∪ `B-/I-{6 типов}` |
| `ClassifExample` | RuMedTop3, RuMedSymptomRec | `text` ← `symptoms` | `label: str` ← `code` | непустой текст |

Ошибка валидации сообщает задачу, файл и номер строки (FR-003).

## Source manifest (`configs/data.yaml`)

```yaml
source:
  repo: sb-ai-lab/MedBench
  commit: dd57f4f4f11aebe4fd18011b109d96b6d331a1bf
files:            # по одному на (задача, сплит)
  - task: RuMedNLI
    split: train
    path: data/RuMedNLI/train_v1.jsonl
    sha256: <hex>
    rows: 11232
site_dir: data/MedBench_data   # опционально, только для отчёта о пересечениях
```

Ожидаемые `rows` — таблица R3 в `research.md`; их проверка = SC-002.

## Хранилище (вне git, FR-012)

```
data/rumedbench/<commit>/<Task>/<split>_v1.jsonl   # скачанные файлы
data/rumedbench/<commit>/manifest.json             # sha256 + время скачивания
```

Идемпотентность (FR-009): файл не скачивается, если существует и его sha256 совпадает с
`configs/data.yaml`.

## Роли (FR-005, FR-006, FR-008)

| Роль | RuMedNLI / RuMedDaNet | RuMedNER / Top3 / SymptomRec | RuMedTest |
|---|---|---|---|
| `train` | open `train` | open `train` | ошибка «нет данных» |
| `tune` | open `dev` | open `dev` | ошибка |
| `final` | open `test` | open `test` | ошибка «меток нет — только submit» |
| `submit` | open `private_test` (= test сайта) | ошибка «нет закрытого test» | open `private_test` |

Инвариант (проверяется при выдаче роли и в тестах): отпечатки `final` не пересекаются с
отпечатками `train` и `tune` той же задачи. Официальные сплиты содержат несколько точных
дубликатов test в train/dev (ADR-014): они удаляются из `train`/`tune`, а их число строк задано в
`known_overlaps` конфига (RuMedNLI tune 2; RuMedNER train 28, tune 7; RuMedSymptomRec train 1).
Любое другое число → `LeakageError`. Данные сайта в роли не входят (research R2).

## Fingerprint

`fingerprint(example) -> str`: SHA-1 от нормализованных входных полей (research R5). Не
включает метку, чтобы находить конфликты меток.

## OverlapReport

- `pairs`: для каждой пары (сплит A, сплит B) из {site train/dev/test} × {open
  train/dev/test/private_test} — число общих отпечатков.
- `label_conflicts`: общие примеры с разными метками.
- `in_split_duplicates`: дубликаты внутри одного сплита.
- Сохраняется в `reports/data/overlap.json` и `reports/data/overlap.md`.

## DatasetStats

По каждой задаче и сплиту: число примеров, распределение меток (top-10 для Top3/SymptomRec),
длины входов в словах (min / median / p95 / max), по 1–2 примера; сравнение размеров со
статьёй. Сохраняется в `reports/data/stats.md`, `reports/data/stats.json`,
`reports/data/length_<task>.png`.
