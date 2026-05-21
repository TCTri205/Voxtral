# Voxtral ASR Quality & Hallucination Report

Source: `results\20-05-2026_v1\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 3.300 | 0 | 45.92% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.887 | 0 | 40.00% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 3.164 | 0 | 44.68% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.435 | 0 | 31.16% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 3.688 | 0 | 66.58% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 3.395 | 0 | 70.67% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 3.308 | 0 | 40.52% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 3.920 | 0 | 40.67% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.637 | 0 | 47.55% | F (Fail) |
| `silence_60s.wav` | success | 0.048 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.047 | 0 | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 47.53% (9/11 files; 2 excluded)**

## Standardized Metrics Summary
- **Average CER (All Files - Silence/Noise Included)**: **38.89%** (11 files)
- **Average CER (Speech Only - Silence/Noise Excluded)**: **47.53%** (9 files)