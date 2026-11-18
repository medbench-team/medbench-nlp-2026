# Contract: CLI и Python API оценки

## CLI (`uv run medbench eval <cmd>`)

| Команда | Что делает | Код выхода |
|---|---|---|
| `eval score <preds.jsonl> --task T --role tune\|final` | Валидирует и считает метрики, печатает их; ничего не сохраняет | 0 / 1 (ошибки валидации со списком id) |
| `eval save <preds.jsonl> --task T --role R --approach A --model M [--params params.json] [--justification TEXT] [--notes TEXT]` | Сохраняет прогон в `results/runs/<run_id>/`, считает метрики (кроме `submit`) | 0 / 1 (в т.ч. `FinalRunExistsError`) |
| `eval rescore <run_dir>` | Пересчитывает метрики по папке, сравнивает с `meta.json` (SC-002) | 0 совпало / 1 |
| `eval leaderboard` | Строит `results/leaderboard.{md,json}` | 0 |
| `eval submit [--run RUN_ID ...] [--naive-fill]` | Собирает zip для medbench.ru | 0 / 1 |
| `eval paper` | Скачивает предсказания моделей статьи (sha256 в `configs/paper_outputs.yaml`), считает метрики и сверяет с таблицей статьи (SC-001) | 0 всё совпало / 1 |

## Python API (`medbench.eval`)

```python
score(task, predictions: list[Prediction], role: Role) -> TaskMetrics      # FR-001, FR-003
overall(per_task: dict[TaskName, TaskMetrics]) -> float | None            # FR-002
save_run(task, role, predictions, *, approach, model, params=None,
         usage=None, justification=None, notes=None) -> Run               # FR-005, FR-006
load_run(run_dir) -> Run
build_leaderboard() -> Leaderboard                                         # FR-007
build_submission(run_ids=None, naive_fill=False) -> Path                    # FR-009
```

Ошибки: `PredictionError` (пропуски/лишние/дубли id, недопустимые значения — с id),
`EvalUnavailableError` (RuMedTest, роль `submit` или `train` для `score`), `FinalRunExistsError`,
`StaleRunError`. Спеки 003–009 сохраняют результаты **только** через `save_run`.
