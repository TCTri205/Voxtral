# LLM-based Hallucination Evaluation Report

- **Run Directory**: `results\18-04-2026_v1`
- **Model Used**: `llama-3.3-70b-versatile`
- **Hallucination Rate**: 88.89%
- **Manual Review Rate**: 100.00%

## Statistics

### Error Type Distribution
| Error Type | Count |
| :--- | :--- |
| insertion | 7 |
| content_replacement | 1 |
| none | 1 |

### Severity Distribution
| Severity | Count |
| :--- | :--- |
| medium | 4 |
| low | 1 |
| high | 3 |
| none | 1 |

## Detailed Results

| File | Hallucination | Error Type | Severity | CER | Review |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | ❌ Yes | insertion | medium | 65.49% | 👀 Manual |
| `media_148284_1767766514646 (1).mp3` | ❌ Yes | insertion | low | 15.77% | 👀 Manual |
| `media_148393_1767860211615 (1).mp3` | ❌ Yes | insertion | medium | 17.55% | 👀 Manual |
| `media_148394_1767860189485 (1).mp3` | ❌ Yes | insertion | medium | 33.67% | 👀 Manual |
| `media_148414_1767922241264 (1).mp3` | ❌ Yes | content_replacement | high | 100.00% | 👀 Manual |
| `media_148439_1767926711644 (1).mp3` | ❌ Yes | insertion | high | 35.10% | 👀 Manual |
| `media_148954_1768789819598 (1).mp3` | ❌ Yes | insertion | medium | 69.48% | 👀 Manual |
| `media_149291_1769069811005.mp3` | ✅ No | none | none | 97.80% | 👀 Manual |
| `media_149733_1769589919400.mp3` | ❌ Yes | insertion | high | 60.43% | 👀 Manual |