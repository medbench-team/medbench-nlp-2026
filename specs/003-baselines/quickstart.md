# Quickstart / Validation: 003-baselines

## Предусловия

`uv sync`; данные скачаны (`uv run medbench data download`); ~1.5 ГБ свободной памяти.

## Сценарии

1. **Подбор (US2)**: `uv run medbench baselines run` → 11 прогонов на `tune` (naive × 5 задач,
   linear × 5; RuMedTest — skip: нет tune) за < 10 мин; `uv run medbench eval leaderboard` →
   таблица «разработка» с naive и linear; финальных прогонов нет.
2. **Финал (US1, SC-001…SC-004)**: `uv run medbench baselines run --role final` → 10 финальных
   прогонов; `uv run medbench baselines report` → `reports/baselines/reproduction.md`:
   Naive ≤ 0.01 по NLI/DaNet/Top3/SymptomRec, NER — с объяснением; linear ≤ 1 п.п. везде;
   `eval leaderboard` → финальные строки naive и linear с Overall.
3. **Повтор финала (US1-3)**: ещё раз `baselines run --role final` → все задачи `skip: final
   уже есть`; новых прогонов нет.
4. **Сабмит (US3, SC-005)**: `uv run medbench baselines run --role submit` → submit-прогоны
   linear (DaNet, NLI) и naive (DaNet, NLI, RuMedTest); `uv run medbench eval submit
   --run <linear DaNet> --run <linear NLI> --run <naive RuMedTest>` → архив без предупреждений.
5. **Время (SC-003)**: суммарно сценарии 1, 2, 4 < 30 мин.
6. **Тесты**: `uv run pytest` — зелёные без сети (бейзлайны на фикстурах).
