# Quickstart / Validation: 002-eval-harness

## Предусловия

- Спека 001 работает, данные скачаны: `uv run medbench data download`.
- Интернет к `raw.githubusercontent.com` — только для сценария 1.

## Сценарии

1. **Воспроизведение статьи (SC-001, US1)**: `uv run medbench eval paper` → таблица 5 наборов
   (naive, TF-IDF, BiLSTM, RuPoolBERT, человек) совпадает с research.md R2, итог «OK: all
   metrics match (≤ 0.01)», код 0.
2. **Оценка без сохранения (US1)**: сгенерировать наивные предсказания для RuMedNLI `tune`
   (всё `neutral`) → `uv run medbench eval score preds.jsonl --task RuMedNLI --role tune` →
   Acc ≈ 33.33. Удалить одну строку → код 1, в сообщении id пропущенного примера.
3. **Отказы (Edge Cases)**: `eval score … --task RuMedTest --role submit` → понятный отказ;
   Top3 с двумя метками в строке → ошибка с id.
4. **Сохранение и пересчёт (US2, SC-002)**: `eval save … --role tune --approach naive --model -`
   → папка `results/runs/<run_id>/`; `eval rescore results/runs/<run_id>` → код 0.
5. **Один final (US2-3, SC-005)**: дважды `eval save … --role final` с теми же approach/model/params
   → второй раз код 1; с `--justification "…"` → сохраняется, обоснование видно в leaderboard.
6. **Сводка (US3, SC-003)**: `uv run medbench eval leaderboard` → `results/leaderboard.md` с
   таблицами final / tune / site, previous art, Δ, Overall «—» для неполных наборов; < 10 с.
7. **Сабмит (US4, SC-004)**: наивные `submit`-прогоны для DaNet/NLI/RuMedTest →
   `uv run medbench eval submit` → zip с тремя файлами, число строк 512 / 1536 / 397, поля как в
   образце сайта.
8. **Тесты**: `uv run pytest` — зелёные без сети (сценарий 1 покрыт тестом с маркером `data`).
