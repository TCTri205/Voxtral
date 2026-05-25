# Voxtral ASR Quality & Hallucination Report

Source: `results\25-05-2026_v2\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | Raw CER | Adjusted CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 1.643 | 0 | 44.02% | 44.02% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 1.159 | 0 | 28.46% | 28.46% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 1.613 | 0 | 35.11% | 35.11% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 1.798 | 0 | 35.18% | 35.18% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 1.456 | 0 | 34.95% | 34.95% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | failed | 0.000 | 0 | N/A | N/A | ERROR |
| `media_148954_1768789819598 (1).mp3` | success | 1.908 | 0 | 28.97% | 28.97% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 1.621 | 0 | 30.19% | 30.19% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.233 | 0 | 51.23% | 51.23% | F (Fail) |
| `silence_60s.wav` | success | 0.054 | 0 | 0.00% | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.055 | 0 | 0.00% | 0.00% | S (Excellent) |

## CER Accounting (Legacy)
- CER files included: **8/10**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth - Legacy): 36.01% (8/10 files; 2 excluded)**

## Standardized Metrics Summary
- **Average Raw CER (All Files - Silence/Noise Included)**: **28.81%** (10 files)
- **Average Adjusted CER (All Files - Silence/Noise Included)**: **28.81%** (10 files)
- **Average Raw CER (Speech Only - Silence/Noise Excluded)**: **36.01%** (8 files)
- **Average Adjusted CER (Speech Only - Silence/Noise Excluded)**: **36.01%** (8 files)