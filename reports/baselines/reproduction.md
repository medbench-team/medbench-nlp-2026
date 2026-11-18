# Воспроизведение бейзлайнов статьи RuMedBench

Сгенерировано `uv run medbench baselines report` по последним финальным прогонам (открытый test). Допуск: naive ≤ 0.01 п.п., linear (TF-IDF + LogReg / CRF) ≤ 1 п.п.

**В допуске: 14 из 15** (ℹ️ — расхождение объяснено, без допуска).

| Подход | Задача | Метрика | Наше | Статья | Δ | |
|---|---|---|---|---|---|---|
| naive | RuMedTop3 | acc | 10.58 | 10.58 | +0.00 | ✅ |
| naive | RuMedTop3 | hit3 | 22.02 | 22.02 | -0.00 | ✅ |
| naive | RuMedSymptomRec | acc | 1.93 | 1.93 | -0.00 | ✅ |
| naive | RuMedSymptomRec | hit3 | 5.30 | 5.30 | +0.00 | ✅ |
| naive | RuMedDaNet | acc | 50.00 | 50.00 | +0.00 | ✅ |
| naive | RuMedNLI | acc | 33.33 | 33.33 | +0.00 | ✅ |
| naive | RuMedNER | acc | 94.31 | 93.66 | +0.65 | ℹ️ |
| naive | RuMedNER | f1 | 54.24 | 51.96 | +2.28 | ℹ️ |
| linear | RuMedTop3 | acc | 49.51 | 49.76 | -0.25 | ✅ |
| linear | RuMedTop3 | hit3 | 71.90 | 72.75 | -0.85 | ✅ |
| linear | RuMedSymptomRec | acc | 30.36 | 32.05 | -1.69 | ❌ |
| linear | RuMedSymptomRec | hit3 | 48.67 | 49.40 | -0.73 | ✅ |
| linear | RuMedDaNet | acc | 51.95 | 51.95 | +0.00 | ✅ |
| linear | RuMedNLI | acc | 59.56 | 59.70 | -0.14 | ✅ |
| linear | RuMedNER | acc | 94.28 | 94.40 | -0.12 | ✅ |
| linear | RuMedNER | f1 | 62.12 | 62.89 | -0.77 | ✅ |
| linear | Overall | - | 57.99 | 58.46 | -0.47 | ✅ |

## Overall

- naive: 35.50 против 35.21 в статье (Δ +0.29)
- linear: 57.99 против 58.46 в статье (Δ -0.47)

## Причины расхождений

- ADR-014: из train удалены точные дубликаты test (RuMedNER — 28 строк, RuMedSymptomRec — 1); официальные модели обучались на сыром train.
- ADR-018: код официального Naive не опубликован; для NER используется «самый частый тег токена в train» (совпадение с официальными предсказаниями ~98% токенов) — сравнение без допуска.
- ADR-019: scikit-learn 1.9 — one-vs-rest через OneVsRestClassifier, max_iter=1000 (в статье — старый LogisticRegression(multi_class='ovr'), max_iter=100); решатели и версии библиотек отличаются.

## Прогоны

- naive / RuMedTop3: `20261117-212401_naive_RuMedTop3_final_0f161807`
- naive / RuMedSymptomRec: `20261117-212402_naive_RuMedSymptomRec_final_0f161807`
- naive / RuMedDaNet: `20261117-212359_naive_RuMedDaNet_final_0f161807`
- naive / RuMedNLI: `20261117-212359_naive_RuMedNLI_final_0f161807`
- naive / RuMedNER: `20261117-212400_naive_RuMedNER_final_0f161807`
- linear / RuMedTop3: `20261117-212834_linear_RuMedTop3_final_d8d9ccfb`
- linear / RuMedSymptomRec: `20261117-213110_linear_RuMedSymptomRec_final_d8d9ccfb`
- linear / RuMedDaNet: `20261117-212456_linear_RuMedDaNet_final_d8d9ccfb`
- linear / RuMedNLI: `20261117-212442_linear_RuMedNLI_final_d8d9ccfb`
- linear / RuMedNER: `20261117-212512_linear_RuMedNER_final_d8d9ccfb`
