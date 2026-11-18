# Quickstart / Validation: 004-llm-ceiling-ollama

## Предусловия

`uv sync`; данные скачаны; `.env` с `OLLAMA_API_KEY`; доступ к `https://ollama.com`.

## Сценарии

1. **Каталог**: `uv run medbench llm models` → 4 модели конфига помечены доступными.
2. **Дымовой прогон (FR-010)**: `uv run medbench llm run --model gemma4:31b --limit 20` → метрики
   на 20 примерах NLI и DaNet, без записи в `results/runs/`.
3. **Потолок на tune (US1, SC-001, SC-006)**: `uv run medbench llm run` → 8 прогонов (4 модели ×
   2 задачи), доля невалидных ≤ 2% у каждой, время ≤ 2 ч на модель.
4. **Кеш (SC-002)**: повторить шаг 3 → 0 новых запросов (в выводе `cache hits = 100%`),
   предсказания идентичны; прервать прогон Ctrl-C и запустить снова — продолжается.
5. **Отчёт (US1-4, SC-003)**: `uv run medbench llm report` → `reports/llm/ceiling.md`, лучшая
   модель по задаче, Δ к TF-IDF (NLI 61.67, DaNet 51.56).
6. **Финал (US2, SC-004)**: `uv run medbench llm run --model <лучшая> --role final` → финальные
   прогоны NLI/DaNet; повтор без `--justification` → `skip`; `eval leaderboard` → строки LLM с Δ.
7. **Сабмит (US3, SC-005)**: `uv run medbench llm run --model <лучшая> --task RuMedTest --task
   RuMedNLI --task RuMedDaNet --role submit` → `uv run medbench eval submit --run …` без
   предупреждений.
8. **Тесты**: `uv run pytest` без сети — парсер, граф и кеш на фейковой модели.
