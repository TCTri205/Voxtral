# Voxtral ASR Quality & Hallucination Report

Source: `results\14-05-2026_v9\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.751 | 0 | 53.80% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.138 | 0 | 51.15% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.184 | 0 | 24.47% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.273 | 0 | 32.16% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 8.284 | 0 | 48.47% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 8.067 | 0 | 41.36% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 2.421 | 0 | 37.41% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 9.380 | 0 | 40.57% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.686 | 0 | 60.12% | F (Fail) |
| `silence_60s.wav` | success | 0.046 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.047 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 43.28% (9/11 files; 2 excluded)**