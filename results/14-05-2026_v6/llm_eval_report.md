# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\14-05-2026_v6`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 81.82%
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
| medium | 6 |
| high | 3 |
| none | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 50.82% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 31.92% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | content_replacement | high | 33.51% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 32.16% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | content_replacement | high | 45.66% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | medium | 36.65% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 38.79% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 37.74% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 55.21% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |