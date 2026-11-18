# Сводная таблица RuMedBench

Сгенерировано `uv run medbench eval leaderboard`. Метрики в %: Top3/SymptomRec — Acc / Hit@3, NER — Acc / F1 (micro по сущностям), остальные — Acc. Overall — среднее 5 задач (две метрики задачи сначала усредняются), только при наличии всех пяти.

## Финальные прогоны (открытый test) против previous art

В скобках — разница с лучшим опубликованным результатом (open test, без человека) по среднему метрик задачи; ★ — SotA. † — повторный final с обоснованием.

| Система | RuMedTop3 | RuMedSymptomRec | RuMedDaNet | RuMedNLI | RuMedNER | Overall |
|---|---|---|---|---|---|---|
| naive · - · 0f161807 | 10.58 / 22.02 (-44.95) | 1.93 / 5.30 (-47.87) | 50.00 (-26.17) | 33.33 (-49.44) | 94.31 / 54.24 (-13.22) | 35.50 |
| linear · - · d8d9ccfb | 49.51 / 71.90 (-0.55) | 30.36 / 48.67 (-11.96) | 51.95 (-24.22) | 59.56 (-23.21) | 94.28 / 62.12 (-9.30) | 57.99 |
| llm-zero-shot · glm-5.3 · 89791f72 | — | — | 98.44 (+22.27 ★) | **86.99** (+4.22 ★) | — | — |
| llm-zero-shot · gemma4:31b · 0b20cdff | — | — | **98.83** (+22.66 ★) | 85.51 (+2.74 ★) | — | — |
| Naive | 10.58 / 22.02 | 1.93 / 5.30 | 50.00 | 33.33 | 93.66 / 51.96 | 35.21 |
| TF-IDF + LogReg/CRF | **49.76 / 72.75** | 32.05 / 49.40 | 51.95 | 59.70 | 94.40 / 62.89 | 58.46 |
| BiLSTM | 40.88 / 63.50 | 20.24 / 31.33 | 52.34 | 60.06 | 94.74 / 63.26 | 53.87 |
| RuBERT | 39.54 / 62.29 | 18.55 / 34.22 | 67.19 | 77.64 | 96.63 / 73.53 | 61.44 |
| RuPoolBERT | 47.45 / 70.44 | 34.94 / 52.05 | 71.48 | 77.29 | 96.47 / 73.15 | 67.20 |
| RuBioBERT | 43.55 / 68.86 | 28.94 / 44.55 | 53.91 | 80.31 | 96.63 / 75.97 | 62.69 |
| RuBioRoBERTa | 46.72 / 72.87 | **44.01 / 58.95** | 76.17 | 82.77 | **97.19 / 77.81** | **71.54** |
| Human | 25.06 / 48.54 | 7.23 / 12.53 | 93.36 | 83.26 | 96.09 / 76.18 | 61.89 |

## Разработка (роль tune, открытый dev)

| Система | RuMedTop3 | RuMedSymptomRec | RuMedDaNet | RuMedNLI | RuMedNER | Overall |
|---|---|---|---|---|---|---|
| naive · - · 0f161807 | 10.26 / 21.11 | 1.93 / 5.06 | 50.00 | 33.31 | 93.94 / 56.37 | 35.53 |
| linear · - · d8d9ccfb | **47.88 / 69.10** | **28.19 / 43.61** | 51.56 | 61.67 | **94.61 / 67.19** | **57.70** |
| llm-zero-shot · gpt-oss:120b · 2248f1db | — | — | 95.31 | 82.05 | — | — |
| llm-zero-shot · glm-5.3 · 89791f72 | — | — | **96.88** | **86.00** | — | — |
| llm-zero-shot · deepseek-v4-pro:0813 · 4ea0502d | — | — | 94.92 | 78.82 | — | — |
| llm-zero-shot · gemma4:31b · 0b20cdff | — | — | 96.48 | 85.00 | — | — |

## Закрытый test сайта medbench.ru

Сравнивать только с нашими сабмитами на сайт (ADR-016).

| Система | RuMedDaNet | RuMedNLI | RuMedTest | Источник |
|---|---|---|---|---|
| ChatGPT (text-davinci-003) | 89.30 | 61.30 | 35.00 | sb-ai-lab/MedBench lb_submissions/SAI/ChatGPT/README.md |

## Источники previous art

- Naive: Blinov et al., 2022 (arXiv:2201.06499), Table 3
- TF-IDF + LogReg/CRF: Blinov et al., 2022, Table 3
- BiLSTM: Blinov et al., 2022, Table 3
- RuBERT: Blinov et al., 2022, Table 3
- RuPoolBERT: Blinov et al., 2022, Table 3
- RuBioBERT: README sb-ai-lab/MedBench; arXiv:2204.03951
- RuBioRoBERTa: README sb-ai-lab/MedBench; arXiv:2204.03951
- Human: Blinov et al., 2022, Table 3 (overall recomputed by us from code/human)
