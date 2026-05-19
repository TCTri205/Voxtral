# Voxtral ASR Quality & Hallucination Report

Source: `results\18-05-2026_v8\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 3.169 | 0 | 43.75% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 5.354 | 0 | 41.54% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.185 | 0 | 30.32% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.275 | 0 | 33.17% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 3.596 | 0 | 46.94% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 9.546 | 0 | 71.15% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 9.351 | 0 | 44.83% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 11.291 | 0 | 39.83% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 4.397 | 0 | 60.74% | F (Fail) |
| `silence_60s.wav` | success | 0.040 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.041 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 45.81% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **37.48%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **45.81%** (9 files)