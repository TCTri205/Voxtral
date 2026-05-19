# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results/18-05-2026_v2`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 81.82%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 100.00%
- **Average CER (All Files - Silence/Noise Included)**: 55.95%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 68.39%
- **Manual Review Rate**: 81.82%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 7 |
| content_replacement | 2 |
| none | 2 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 4 |
| high | 5 |
| none | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 81.25% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 69.62% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | content_replacement | high | 60.64% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 72.36% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | content_replacement | high | 68.88% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 60.58% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | high | 61.38% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 66.56% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 74.23% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |