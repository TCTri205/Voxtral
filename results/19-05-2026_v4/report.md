# Voxtral ASR Quality & Hallucination Report

Source: `results\19-05-2026_v4\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.800 | 0 | 53.80% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 3.002 | 0 | 34.62% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.185 | 0 | 24.47% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.275 | 0 | 32.16% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 2.561 | 0 | 47.96% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.810 | 0 | 46.15% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 2.474 | 0 | 37.76% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 3.342 | 0 | 47.17% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.911 | 0 | 61.66% | F (Fail) |
| `silence_60s.wav` | success | 0.047 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.046 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 42.86% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **35.07%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **42.86%** (9 files)