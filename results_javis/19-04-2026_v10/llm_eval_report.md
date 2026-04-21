# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results_javis\19-04-2026_v10`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 90.91%
- **Manual Review Rate**: 90.91%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 8 |
| content_replacement | 1 |
| silence_text | 1 |
| none | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 6 |
| high | 4 |
| none | 1 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 27.99% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 25.38% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 29.26% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 17.09% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | medium | 40.56% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | content_replacement | high | 82.21% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | high | 34.66% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 19.92% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 50.61% | 👀 Manual |
| `silence_60s.wav` | ❌ Yes | silence_text | high | 0.00% | 👀 Manual |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |