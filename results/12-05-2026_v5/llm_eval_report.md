# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\12-05-2026_v5`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 100.00%
- **Manual Review Rate**: 100.00%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 6 |
| content_replacement | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 5 |
| high | 2 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 61.96% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | medium | 49.23% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 40.43% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 32.16% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | content_replacement | high | 47.19% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 47.60% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 36.90% | 👀 Manual |