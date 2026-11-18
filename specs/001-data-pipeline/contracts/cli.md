# Contract: CLI и Python API данных

## CLI (`uv run medbench data <cmd>`)

| Команда | Что делает | Код выхода |
|---|---|---|
| `data download [--force]` | Скачивает открытые файлы по `configs/data.yaml`, проверяет sha256 и схему, печатает таблицу «задача × сплит × строк». Без `--force` пропускает уже проверенные файлы. | 0 — ок; 1 — сеть/sha256/схема (сообщение с задачей, файлом, строкой) |
| `data verify` | Проверяет локальные файлы без сети: sha256, число строк, схема, инвариант ролей. | 0 / 1 |
| `data overlap` | Строит отчёт о пересечениях сайт × open; без `data/MedBench_data` — предупреждение и отчёт только по open. | 0 |
| `data stats` | Строит `reports/data/stats.{md,json}` и гистограммы длин. | 0 |

Все команды работают из корня репозитория; путь к конфигу — `--config configs/data.yaml`
(по умолчанию).

Пример вывода `data download`:

```
RuMedBench @ dd57f4f · data/rumedbench/dd57f4f…/
task              train   dev   test  private_test
RuMedNLI          11232  1395   1422          1536
RuMedDaNet         1052   256    256           512
RuMedTest             -     -      -           397
...
site data: data/MedBench_data found (3 tasks)
```

## Python API (`medbench.data`)

```python
load_split(task: TaskName, split: SourceSplit) -> list[Example]
get_role(task: TaskName, role: Role) -> list[Example]        # FR-005/006/008
fingerprint(example: Example) -> str
```

- `get_role` бросает `RoleUnavailableError` с человекочитаемым объяснением (например,
  «RuMedTest: размеченных данных нет, доступна только роль submit»).
- `get_role` для `train`/`tune` исключает известные дубликаты `final` (`known_overlaps`, ADR-014) и
  бросает `LeakageError`, если их число отличается от заявленного.
- Функции не ходят в сеть; если файлы не скачаны — `DataNotFoundError` с подсказкой
  `uv run medbench data download`.

Эти функции — точка входа для спек 002–009; менять сигнатуры можно только с обновлением
контракта.
