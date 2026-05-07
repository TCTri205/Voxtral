# Voxtral ASR Quality & Hallucination Report

Source: `results\07-05-2026_v3\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 2.411 | 0 | 55.43% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 2.256 | 0 | 34.62% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 2.379 | 0 | 48.40% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 2.269 | 0 | 34.17% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 2.556 | 0 | 56.38% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 2.365 | 0 | 31.73% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 2.475 | 0 | 31.38% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 2.384 | 0 | 54.30% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 1.501 | 0 | 61.04% | F (Fail) |
| `silence_60s.wav` | success | 0.049 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.042 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 45.27% (9/11 files; 2 excluded)**