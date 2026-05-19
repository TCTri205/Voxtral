# Voxtral ASR Quality & Hallucination Report

Source: `results\19-05-2026_v7\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 3.928 | 0 | 42.12% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 3.624 | 0 | 52.31% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.958 | 0 | 40.96% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.268 | 0 | 39.20% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 3.493 | 0 | 46.43% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 5.581 | 0 | 55.29% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 3.358 | 0 | 52.41% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 2.675 | 0 | 32.81% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.636 | 0 | 54.29% | F (Fail) |
| `silence_60s.wav` | success | 0.043 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.040 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 46.20% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **37.80%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **46.20%** (9 files)