# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results_javis\19-04-2026_v4`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 81.82%
- **Manual Review Rate**: 90.91%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 8 |
| none | 2 |
| silence_text | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 6 |
| high | 3 |
| none | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 38.59% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 25.77% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 26.60% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 27.14% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 38.27% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 94.71% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 29.48% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ✅ No | none | none | 158.60% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 50.31% | 👀 Manual |
| `silence_60s.wav` | ❌ Yes | silence_text | high | 0.00% | 👀 Manual |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |