# Voxtral ASR Quality & Hallucination Report

Source: `results\25-05-2026_v1\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | Raw CER | Adjusted CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 1.503 | 0 | 57.34% | 57.34% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 1.030 | 0 | 27.31% | 27.31% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 1.406 | 0 | 20.74% | 20.74% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 1.158 | 0 | 33.17% | 33.17% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 1.341 | 0 | 50.00% | 50.00% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 1.497 | 0 | 36.06% | 36.06% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 1.693 | 0 | 33.28% | 33.28% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 1.267 | 0 | 42.77% | 42.77% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.090 | 0 | 50.61% | 50.61% | F (Fail) |
| `silence_60s.wav` | success | 0.046 | 0 | 0.00% | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.047 | 0 | 0.00% | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 39.03% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average Raw CER (All Files - Silence/Noise Included)**: **31.93%** (11 files)
- **Average Adjusted CER (All Files - Silence/Noise Included)**: **31.93%** (11 files)
- **Average Raw CER (Speech Only - Silence/Noise Excluded)**: **39.03%** (9 files)
- **Average Adjusted CER (Speech Only - Silence/Noise Excluded)**: **39.03%** (9 files)