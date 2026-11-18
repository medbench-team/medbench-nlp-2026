# Дорожная карта MedBench NLP 2026

Цель: SotA на русскоязычном медицинском бенчмарке RuMedBench (RuMedNLI, RuMedDaNet, RuMedTest;
расширение — RuMedNER, RuMedTop3, RuMedSymptomRec) с честным сравнением с previous art.
Разработка ведётся **спека за спекой** через GitHub Spec Kit.

Правила проекта — [`.specify/memory/constitution.md`](../.specify/memory/constitution.md),
инструкции для агентов — [`CLAUDE.md`](../CLAUDE.md).

## Previous art (%)

**Открытый test RuMedBench** — здесь заявляем SotA (ADR-016):

| Задача | Лучший опубликованный результат | Человек |
|---|---|---|
| RuMedNLI (Acc) | 82.77 — RuBioRoBERTa | 83.26 |
| RuMedDaNet (Acc) | **76.17 — RuBioRoBERTa** | 93.36 |
| RuMedNER (Acc / F1) | 97.19 / 77.81 — RuBioRoBERTa | 96.09 / 76.18 |
| RuMedTop3 (Acc / Hit@3) | 49.76 — TF-IDF / 72.87 — RuBioRoBERTa | 25.06 / 48.54 |
| RuMedSymptomRec (Acc / Hit@3) | 44.01 / 58.95 — RuBioRoBERTa | 7.23 / 12.53 |
| Overall | 71.54 — RuBioRoBERTa | 61.89 |

**Закрытый test сайта medbench.ru** (сравнивается только с нашими сабмитами):

| Задача | Результат |
|---|---|
| RuMedDaNet (Acc) | 89.3 — ChatGPT (text-davinci-003) |
| RuMedNLI (Acc) | 61.3 — ChatGPT |
| RuMedTest (Acc) | 35.0 — ChatGPT (случайный ответ ≈ 24.9) |

F1 для NER — micro-F1 по сущностям (как `seqeval.f1_score` в официальном `code/eval.py`).
Источники: Blinov et al., 2022 (arXiv:2201.06499, табл. 3), README github.com/sb-ai-lab/MedBench
(RuBioRoBERTa, arXiv:2204.03951), `lb_submissions/SAI/ChatGPT`. Все цифры — в
`configs/previous_art.yaml` (спека 002).

## Данные

| Источник | Метки test | Для чего |
|---|---|---|
| Открытый RuMedBench (github.com/sb-ai-lab/MedBench @ `dd57f4f`) | есть (кроме `private_test` и RuMedTest) | train — обучение, **dev — подбор**, test — **один финальный прогон** → сравнение с previous art; `private_test` → сабмит |
| Сайт medbench.ru (`data/MedBench_data/`, не в git) | нет | **только сверка** (ADR-013): train сайта = open train + dev, **dev сайта = open test**, test сайта = open `private_test` побайтово |

> ⚠️ dev сайта нельзя использовать для подбора — это открытый test (ADR-012, спека 001).
> У RuMedTest меток нет нигде: качество — только сабмитом на medbench.ru.

ECG2Pathology исключена (сигналы ЭКГ, а не текст).

## Спеки

Каждая спека: ветка `NNN-short-name` от `dev` → `/speckit-specify` → `/speckit-plan` →
`/speckit-tasks` → `/speckit-implement` → PR в `dev` → холст `NNN <name>` в Klyaksa.

| # | Спека | Что даёт | Зависит от | Где считается | Статус |
|---|---|---|---|---|---|
| 001 | `data-pipeline` | Загрузка открытого RuMedBench @ `dd57f4f`; Pydantic-схемы; роли train/tune/final/submit без утечек; отчёт о пересечениях с данными сайта; EDA и статистика для раздела Dataset | — | сервер | 🟦 |
| 002 | `eval-harness` | Метрики как в официальном `eval.py` (Acc, Hit@3, NER micro-F1, Overall), проверка на предсказаниях моделей статьи; формат `results/<run_id>/preds.jsonl` + `meta.json`; сводная таблица vs previous art; экспорт сабмита для medbench.ru | 001 | сервер | 🟦 |
| 003 | `baselines` | Naive + TF-IDF (char 3–8) + LogReg / CRF: воспроизведение цифр статьи, первый полный цикл и первый сабмит | 001, 002 | сервер (CPU), ~7 мин | 🟦 |
| **004** | **`llm-ceiling-ollama`** | **Потолок LLM: gpt-oss:120b, glm-5.3, deepseek-v4-pro, gemma4:31b (Ollama Cloud) через LangChain `ChatOllama` + граф LangGraph; zero-shot на NLI / DaNet (tune → final) и RuMedTest (submit)** | 001, 002 | Ollama Cloud | 🟦 |
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
  `OLLAMA_API_KEY` из `.env` (заголовок `Authorization: Bearer` через `client_kwargs`),
  `temperature=0`, `reasoning=True` (проверено живыми вызовами, research R2).
- **Модели (clarify):** `gpt-oss:120b`, `glm-5.3`, `deepseek-v4-pro:0813`, `gemma4:31b` из 24 в
  каталоге; остальные добавляются конфигом `configs/llm_ceiling.yaml`.
- **Граф LangGraph** (один на все задачи): `build_prompt` → проверка кеша → `call_llm` →
  `parse` (строка «Ответ: …» + русские синонимы — **облако игнорирует `format`/JSON-схему**,
  ADR-020) → `validate` → `reprompt` (до 2 раз) → `fallback` (метка по умолчанию + `invalid=true`).
- **Прогон:** `graph.abatch(max_concurrency=4)`, экспоненциальная пауза при 429/5xx, кеш
  ответов в SQLite вне git, лог токенов и латентности.
- **Где меряем:** роль `tune` (open dev); открытый test (`final`) — один финальный прогон.
  RuMedTest — меток нет (проверено в 001), только сабмит `private_test` на сайт.
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
| 03 Decisions (ADR) | ADR-001…020 (ADR-003 заменён ADR-020) | `eaa9345d-c899-4fed-b265-af4bc1833afc` |
| 001 data-pipeline | Загрузка, роли сплитов, пересечения, EDA | `f271f48c-fff4-495c-98a9-afa48a2bad09` |
| 002 eval-harness | Сохранение прогонов, метрики, сводка, сабмит | `9aa75117-eef6-4cd3-bb6c-42951122cb0e` |
| 003 baselines | Naive и TF-IDF/CRF, поток обучения и сохранения | `696157e7-7db2-4631-8567-61f907f3988f` |
| 004 LLM ceiling (Ollama + LangGraph) | Граф LangGraph и поток прогона | `691a83e8-0946-4fb2-8c89-9a265eec5690` |

## Открытые вопросы

- ~~Есть ли метки RuMedTest в открытом репозитории?~~ Нет (спека 001): только сабмит.
- Формат сабмита на medbench.ru (написать на medbench@yandex.ru или открыть issue).
- Лимиты и квоты Ollama Cloud на ~3 000 запросов на модель (dev + test трёх задач).
- Дедлайн сдачи проекта; кто из команды берёт GPU-спеки (006, 008).
