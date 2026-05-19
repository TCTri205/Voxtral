# Voxtral ASR Quality & Hallucination Report

Source: `results\18-05-2026_v3\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 1.362 | 0 | 80.98% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 1.638 | 0 | 67.31% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 1.598 | 0 | 59.57% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 0.998 | 0 | 71.86% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 1.342 | 0 | 68.62% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 1.641 | 0 | 59.13% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 1.273 | 0 | 60.69% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 1.491 | 0 | 65.62% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 0.862 | 0 | 74.54% | F (Fail) |
| `silence_60s.wav` | success | 0.048 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.061 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 67.59% (9/11 files; 2 excluded)**