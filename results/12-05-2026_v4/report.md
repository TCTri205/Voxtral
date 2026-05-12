# Voxtral ASR Quality & Hallucination Report

Source: `results\12-05-2026_v4\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.680 | 0 | 61.68% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.141 | 0 | 49.23% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.388 | 0 | 39.89% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.275 | 0 | 32.16% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 4.060 | 0 | 42.09% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.807 | 0 | 32.69% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 2.838 | 0 | 35.52% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 3.028 | 0 | 29.45% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.360 | 0 | 57.67% | F (Fail) |
| `silence_60s.wav` | success | 0.057 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.048 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 42.27% (9/11 files; 2 excluded)**