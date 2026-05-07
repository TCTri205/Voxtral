# Voxtral ASR Quality & Hallucination Report

Source: `results\07-05-2026_v5\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 3.157 | 0 | 39.40% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 3.995 | 0 | 38.46% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 3.745 | 0 | 31.38% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.443 | 0 | 34.17% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 3.592 | 0 | 55.61% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.519 | 0 | 31.73% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 3.361 | 0 | 30.86% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 3.603 | 0 | 41.82% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 2.052 | 0 | 42.94% | F (Fail) |
| `silence_60s.wav` | success | 0.049 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.049 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 38.49% (9/11 files; 2 excluded)**