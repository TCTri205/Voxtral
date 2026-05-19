# Voxtral ASR Quality & Hallucination Report

Source: `results\18-05-2026_v6\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.433 | 0 | 47.01% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.380 | 0 | 38.85% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.374 | 0 | 40.43% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 3.070 | 0 | 47.24% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 9.031 | 0 | 40.05% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.818 | 0 | 28.37% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 2.889 | 0 | 29.83% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 8.099 | 0 | 34.38% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 3.525 | 0 | 66.87% | F (Fail) |
| `silence_60s.wav` | success | 0.049 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.044 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 41.45% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **33.91%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **41.45%** (9 files)