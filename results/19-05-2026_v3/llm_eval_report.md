# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\19-05-2026_v3`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 72.73%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 88.89%
- **Average CER (All Files - Silence/Noise Included)**: 40.71%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 49.76%
- **Manual Review Rate**: 81.82%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 8 |
| none | 3 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 6 |
| high | 2 |
| none | 3 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 51.36% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 31.15% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 64.89% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 44.22% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 56.89% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | medium | 28.85% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | high | 46.55% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ✅ No | none | none | 57.34% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 66.56% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |