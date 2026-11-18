# Quickstart / Validation: 001-data-pipeline

## Предусловия

- `uv` установлен; доступ в интернет к `raw.githubusercontent.com`.
- (Опционально) `data/MedBench_data/` с версией сайта — для отчёта о пересечениях.

## Сценарии проверки

1. **Установка**: `uv sync` — без ошибок.
2. **Загрузка (US1, SC-001, SC-002)**: `rm -rf data/rumedbench && time uv run medbench data download`
   → < 5 минут; таблица совпадает с `research.md` R3 (NLI 11232/1395/1422/1536, DaNet
   1052/256/256/512, RuMedTest 397, NER 3440/676/693, Top3 4690/848/822, SymptomRec
   2470/415/415).
3. **Идемпотентность (SC-005)**: повторный `uv run medbench data download` → < 10 с, без
   скачиваний («skipped: verified»).
4. **Порча файла (US1-3)**: удалить поле в одной строке скачанного файла →
   `uv run medbench data verify` выходит с кодом 1 и называет задачу, файл и строку.
   Восстановить: `uv run medbench data download --force`.
5. **Роли без утечек (US2, SC-003)**:
   `uv run python -c "from medbench.data import get_role; print(len(get_role('RuMedNLI','tune')))"`
   → `1393` (open dev 1395 − 2 дубликата test, ADR-014); `get_role('RuMedTest','final')` → `RoleUnavailableError` с объяснением.
6. **Пересечения (SC-004)**: `uv run medbench data overlap` → `reports/data/overlap.md`
   содержит: site dev ∩ open test = 1421 (NLI) и 256 (DaNet); site test = open private_test.
7. **Статистика (US3, SC-006)**: `uv run medbench data stats` → `reports/data/stats.md` с
   разделами для 6 задач и PNG-гистограммами.
8. **Тесты**: `uv run pytest` — зелёные, без сети (проверить с отключённой сетью).
