# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\05-05-2026_v2`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 81.82%
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
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 48.91% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 58.85% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 47.87% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 32.16% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | insertion | high | 55.36% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 35.10% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 34.14% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ❌ Yes | insertion | medium | 54.51% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | medium | 56.13% | 👀 Manual |
| `silence_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |
| `stochastic_noise_60s.wav` | ✅ No | none | none | 0.00% | 🤖 Auto |