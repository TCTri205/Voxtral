# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\20-05-2026_v1`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 81.82%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 100.00%
- **Average CER (All Files - Silence/Noise Included)**: 38.89%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 47.53%
- **Manual Review Rate**: 81.82%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 9 |
| none | 2 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 7 |
| high | 2 |
| none | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 45.92% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 40.00% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 44.68% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 31.16% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 66.58% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 70.67% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 40.52% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 40.67% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 47.55% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |