# Voxtral ASR Quality & Hallucination Report

Source: `results\14-05-2026_v4\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.645 | 0 | 48.91% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 3.252 | 0 | 31.54% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.402 | 0 | 35.11% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 1.952 | 0 | 48.24% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 2.652 | 0 | 40.56% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.955 | 0 | 45.03% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 3.151 | 0 | 31.03% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 2.832 | 0 | 26.73% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.413 | 0 | 62.88% | F (Fail) |
| `silence_60s.wav` | success | 0.061 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.048 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 41.11% (9/11 files; 2 excluded)**