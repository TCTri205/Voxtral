# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\25-05-2026_v2`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 70.00%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 87.50%
- **Average CER (All Files - Silence/Noise Included)**: 28.81%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 36.01%
- **Manual Review Rate**: 70.00%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 6 |
| none | 3 |
| content_replacement | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 5 |
| none | 3 |
| high | 1 |
| low | 1 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 44.02% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ✅ No | none | none | 28.46% | 🤖 Auto |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 35.11% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 35.18% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | content_replacement | high | 34.95% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 28.97% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 30.19% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | low | 51.23% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |