# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results/18-05-2026_v4`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 81.82%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 100.00%
- **Average CER (All Files - Silence/Noise Included)**: 33.48%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 40.93%
- **Manual Review Rate**: 81.82%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 8 |
| content_replacement | 1 |
| none | 2 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 5 |
| high | 4 |
| none | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 53.80% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 28.85% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 24.47% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 32.16% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | high | 47.96% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 30.29% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 37.07% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | high | 51.15% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | content_replacement | high | 62.58% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |