# Contract: CLI бейзлайнов

## `uv run medbench baselines run`

| Опция | По умолчанию | Описание |
|---|---|---|
| `--approach naive\|linear\|all` | `all` | какие бейзлайны |
| `--task T` (повторяемая) | все 6 задач | задачи |
| `--role tune\|final\|submit` (повторяемая) | `tune` | роли; `final` и `submit` — только явно |
| `--justification TEXT` | — | для повторного `final` (правило спеки 002) |

Вывод — строка на прогон: `approach task role → metrics | saved <run_id>` или `skip: <причина>`.
Код выхода 1 только при ошибке данных/валидации; уже существующий `final` и недоступная роль —
не ошибки (сообщение `skip`).

## `uv run medbench baselines report`

Строит `reports/baselines/reproduction.{md,json}` из последних `final`-прогонов `naive` и
`linear`; печатает таблицу «наше / статья / Δ» и итог «в допуске: N из M». Код 1, если нет
финальных прогонов.

## Python API (`medbench.baselines`)

```python
NaiveBaseline(); LinearBaseline()              # .approach, .params, .fit(task, train), .predict(task, examples)
run_baselines(approaches, tasks, roles, justification=None) -> list[RunOutcome]
build_reproduction_report() -> ReproductionReport
```
