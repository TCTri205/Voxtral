# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\20-05-2026_v2`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate (All Files - Silence/Noise Included)**: 81.82%
- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: 100.00%
- **Average CER (All Files - Silence/Noise Included)**: 29.99%
- **Average CER (Speech Only - Silence/Noise Excluded)**: 36.66%
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
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 39.13% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 23.08% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 22.34% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 30.65% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 36.22% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 68.27% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 24.83% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 37.53% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 47.85% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |