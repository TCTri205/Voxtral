# Voxtral ASR Quality & Hallucination Report

Source: `results\21-05-2026_v3\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 1.497 | 0 | 44.02% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 1.017 | 0 | 31.54% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 1.399 | 0 | 35.11% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 1.788 | 0 | 36.18% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 1.336 | 0 | 34.95% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.222 | 0 | 26.44% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 1.900 | 0 | 28.97% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 1.587 | 0 | 35.32% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.179 | 0 | 51.23% | F (Fail) |
| `silence_60s.wav` | success | 0.052 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.046 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 35.97% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **29.43%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **35.97%** (9 files)