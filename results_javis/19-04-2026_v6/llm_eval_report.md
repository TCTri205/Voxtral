# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results_javis\19-04-2026_v6`
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
| medium | 5 |
| high | 5 |
| none | 1 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 31.52% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 26.54% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | high | 29.79% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 24.12% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 39.03% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 29.33% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | high | 29.31% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 18.66% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 45.71% | 👀 Manual |
| `silence_60s.wav` | ❌ Yes | silence_text | high | 0.00% | 👀 Manual |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |