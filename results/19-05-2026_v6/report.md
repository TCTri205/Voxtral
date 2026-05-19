# Voxtral ASR Quality & Hallucination Report

Source: `results\19-05-2026_v6\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 3.531 | 0 | 48.10% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.760 | 0 | 40.00% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.178 | 0 | 32.98% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.268 | 0 | 31.16% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 4.250 | 0 | 58.42% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 3.095 | 0 | 70.67% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 3.096 | 0 | 61.03% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 3.118 | 0 | 36.90% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.681 | 0 | 49.69% | F (Fail) |
| `silence_60s.wav` | success | 0.042 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.043 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 47.66% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **39.00%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **47.66%** (9 files)