# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results_javis\19-04-2026_v2`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 90.91%
- **Manual Review Rate**: 90.91%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 9 |
| silence_text | 1 |
| none | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 7 |
| high | 3 |
| none | 1 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 29.08% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 24.62% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 28.19% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 28.14% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 39.29% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | medium | 27.88% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 33.97% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | high | 181.66% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 40.80% | 👀 Manual |
| `silence_60s.wav` | ❌ Yes | silence_text | high | 0.00% | 👀 Manual |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |