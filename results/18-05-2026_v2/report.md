# Voxtral ASR Quality & Hallucination Report

Source: `results\18-05-2026_v2\results.json`
HRS (Hallucination Rate on Silence): **0.000 CPM**

## Detailed Results per File

| File | Status | RTF (Inf) | HRS/RF | CER | Grade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | success | 1.375 | 0 | 81.25% | F (Fail) |
| `media_148284_1767766514646 (1).mp3` | success | 1.643 | 0 | 69.62% | F (Fail) |
| `media_148393_1767860211615 (1).mp3` | success | 1.601 | 0 | 60.64% | F (Fail) |
| `media_148394_1767860189485 (1).mp3` | success | 0.998 | 0 | 72.36% | F (Fail) |
| `media_148414_1767922241264 (1).mp3` | success | 1.342 | 0 | 68.88% | F (Fail) |
| `media_148439_1767926711644 (1).mp3` | success | 1.643 | 0 | 60.58% | F (Fail) |
| `media_148954_1768789819598 (1).mp3` | success | 1.277 | 0 | 61.38% | F (Fail) |
| `media_149291_1769069811005.mp3` | success | 1.501 | 0 | 66.56% | F (Fail) |
| `media_149733_1769589919400.mp3` | success | 0.901 | 0 | 74.23% | F (Fail) |
| `silence_60s.wav` | success | 0.047 | 0 | 0.00% | S (Excellent) |
| `stochastic_noise_60s.wav` | success | 0.057 | 0 | 0.00% | S (Excellent) |

## CER Accounting
- CER files included: **9/11**
- CER excluded files: **2**
  - Empty-on-speech (Fail): 0
  - Silence/Noise (Intentional): 2
- Empty-on-speech count: **0**
- Deletion count: **0**
- Excluded from CER average: `silence_60s.wav`, `stochastic_noise_60s.wav`

**Average CER (Ground Truth): 68.39% (9/11 files; 2 excluded)**