# Дорожная карта MedBench NLP 2026

Цель: SotA на русскоязычном медицинском бенчмарке RuMedBench (RuMedNLI, RuMedDaNet, RuMedTest;
расширение — RuMedNER, RuMedTop3, RuMedSymptomRec) с честным сравнением с previous art.
Разработка ведётся **спека за спекой** через GitHub Spec Kit.

Правила проекта — [`.specify/memory/constitution.md`](../.specify/memory/constitution.md),
инструкции для агентов — [`CLAUDE.md`](../CLAUDE.md).

## Previous art (открытый test RuMedBench, %)

| Задача | Лучший опубликованный результат | Человек |
|---|---|---|
| RuMedNLI (Acc) | 82.77 — RuBioRoBERTa | 83.26 |
| RuMedDaNet (Acc) | 89.3 — ChatGPT (text-davinci-003) | 93.36 |
| RuMedTest (Acc) | 35.0 — ChatGPT | — |
| RuMedNER (Acc/F1) | 97.19 / 77.81 — RuBioRoBERTa | 96.09 / 76.18 |
| RuMedTop3 (Acc/Hit@3) | 49.76 / 72.87 | 25.06 / 48.54 |
| RuMedSymptomRec (Acc/Hit@3) | 44.01 / 58.95 — RuBioRoBERTa | 7.23 / 12.53 |

Источник: Blinov et al., 2022 (arXiv:2201.06499), README github.com/sb-ai-lab/MedBench.

## Данные

| Источник | Метки test | Для чего |
|---|---|---|
| Открытый RuMedBench (github.com/sb-ai-lab/MedBench) | есть | train/dev — разработка, test — **один финальный прогон** → сравнение с previous art |
| Сайт medbench.ru (`data/MedBench_data/`, не в git) | нет | доп. train/dev после дедупликации с open test; test → сабмит на лидерборд |

ECG2Pathology исключена (сигналы ЭКГ, а не текст).

## Спеки

Каждая спека: ветка `NNN-short-name` от `dev` → `/speckit-specify` → `/speckit-plan` →
`/speckit-tasks` → `/speckit-implement` → PR в `dev` → холст `NNN <name>` в Klyaksa.

| # | Спека | Что даёт | Зависит от | Где считается | Статус |
|---|---|---|---|---|---|
| 001 | `data-pipeline` | Загрузка открытого RuMedBench и данных сайта; Pydantic-схемы; проверка пересечений (дедупликация); EDA и статистика для раздела Dataset | — | сервер | ⬜ |
| 002 | `eval-harness` | Метрики (Acc, Hit@3, macro-F1, Overall как в статье); формат `results/<run_id>/preds.jsonl` + `meta.json`; сводная таблица vs previous art; экспорт сабмита для medbench.ru | 001 | сервер | ⬜ |
| 003 | `baselines` | Naive + TF-IDF (char 3–8) + LogReg: воспроизведение цифр статьи, проверка пайплайна | 001, 002 | сервер (CPU) | ⬜ |
| **004** | **`llm-ceiling-ollama`** | **Потолок LLM: крупнейшие модели Ollama Cloud через LangChain `ChatOllama`, оркестрация LangGraph; zero-shot на NLI / DaNet / RuMedTest** | 001, 002 | Ollama Cloud | ⬜ |
| 005 | `prompting` | Few-shot (подбор примеров из train), CoT, self-consistency; выбор лучших промптов на dev | 004 | Ollama Cloud | ⬜ |
| 006 | `encoder-finetune` | Дообучение RuBioRoBERTa / ruRoBERTa-large / multilingual-e5 на NLI и DaNet | 001, 002 | Colab / Kaggle GPU | ⬜ |
| 007 | `rag-rumedtest` | RAG по медицинским источникам для RuMedTest (ретривер + LLM из 004) | 004 | сервер + Ollama Cloud | ⬜ |
| 008 | `lora-llm` (опц.) | LoRA / QLoRA на train NLI / DaNet | 006 | GPU | ⬜ |
| 009 | `ensemble-and-submit` | Ансамбль, анализ ошибок (негации, аббревиатуры, единицы), финальные прогоны на test, сабмит на medbench.ru | 003–007 | сервер | ⬜ |
| 010 | `report` | Отчёт по шаблону курса (LaTeX), README, таблицы и графики из 002 | все | — | ⬜ |

Статусы: ⬜ запланировано · 🟦 в работе · ✅ смержено в `dev`. Цвет блока на холсте
«00 Roadmap» меняется вместе со статусом.

### 004 `llm-ceiling-ollama` — подробнее

Зачем: узнать максимум, который дают крупнейшие LLM без дообучения, и по нему решить, какие
задачи закрывать LLM, а какие — энкодерами.

- **Провайдер:** `langchain-ollama` `ChatOllama`, `base_url=https://ollama.com`, ключ
  `OLLAMA_API_KEY` из `.env` (заголовок `Authorization: Bearer`), `temperature=0`.
  Точные параметры конструктора сверить через context7 при `/speckit-plan`.
- **Модели:** список из `GET https://ollama.com/v1/models` в момент запуска; берём
  крупнейшие (класса gpt-oss-120b, qwen3 235B/480B, deepseek-v3.x, kimi, gemma). Итоговый
  список фиксируется в спеке и в `meta.json`.
- **Граф LangGraph** (один на все задачи): `build_prompt` → проверка кеша → `call_llm` →
  `parse` (structured output: Pydantic с enum меток `entailment|contradiction|neutral`,
  `да|нет`, `1|2|3|4`) → `validate` → при невалидном ответе `retry` (до N раз) →
  `fallback` (метка по умолчанию + `invalid=true`).
- **Прогон:** батчи с семафором параллельности и rate-limit, дисковый кеш, лог токенов и
  латентности.
- **Где меряем:** dev; открытый test — один финальный прогон. RuMedTest — по меткам из
  открытого репозитория (наличие проверяется в 001), иначе только сабмит на сайт.
- **Результат:** таблица «модель × задача» vs previous art + вывод для спек 005–007.

## Архитектура кода (закрепляется в 001–002)

```
pyproject.toml          # uv, Python 3.12
src/medbench/
  data/       # загрузчики, Pydantic-схемы, сплиты, дедупликация
  tasks/      # описания задач: метки, промпты, метрики
  eval/       # метрики, preds.jsonl, сводные таблицы, сабмит
  baselines/  # naive, tfidf
  llm/        # провайдер Ollama, граф LangGraph, кеш
  cli.py      # uv run medbench <cmd>
configs/      # YAML-конфиги прогонов
results/      # предсказания и метрики (в git — только сводки)
notebooks/    # обучение на Colab/Kaggle
tests/        # pytest, без сети
```

## Схемы в Klyaksa

Проект **MedBench** (личный workspace «My Space»). Каждая новая спека добавляет свой холст
`NNN <name>`, каждое решение — стикер ADR на «03 Decisions (ADR)».

| Холст | Что на нём | Canvas ID |
|---|---|---|
| 00 Roadmap | Спеки 001–010, зависимости, статусы | `29b61eea-cd59-4c5d-9e9e-197c99294fa8` |
| 01 Architecture | Модули `src/medbench` и внешние системы | `19a8dfe0-5002-40a7-9739-671059756861` |
| 02 Data & Evaluation | Какие данные для чего, правила работы с test | `f9701999-5430-451e-80c3-08c55070d032` |
| 03 Decisions (ADR) | ADR-001…011 | `eaa9345d-c899-4fed-b265-af4bc1833afc` |
| 004 LLM ceiling (Ollama + LangGraph) | Граф LangGraph и поток прогона | `691a83e8-0946-4fb2-8c89-9a265eec5690` |

## Открытые вопросы

- Есть ли метки RuMedTest в открытом репозитории (проверяется в 001)?
- Формат сабмита на medbench.ru (написать на medbench@yandex.ru или открыть issue).
- Лимиты и квоты Ollama Cloud на ~3 000 запросов на модель (dev + test трёх задач).
- Дедлайн сдачи проекта; кто из команды берёт GPU-спеки (006, 008).
