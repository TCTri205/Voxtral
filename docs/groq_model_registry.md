# Groq Model Registry

This document lists the models available on the Groq Free Tier as of April 2026. Use this list for fallback purposes or when specific model characteristics are required.

## Primary Model (Recommended)

- **Model ID**: `llama-3.3-70b-versatile`
- **Speed**: 280 T/s
- **Context Window**: 131k
- **Usage**: Main model for hallucination evaluation and complex reasoning.

## Fallback / Preview Models

| Model ID | Speed (T/s) | Context Window | Notes |
|----------|-------------|----------------|-------|
| `llama-3.1-8b-instant` | 560 | 131k | Fast, lightweight |
| `openai/gpt-oss-120b` | 500 | 131k | High capacity |
| `openai/gpt-oss-20b` | 1000 | 131k | Extreme speed |
| `qwen/qwen3-32b` | 400 | 131k | Alternative reasoning |
| `whisper-large-v3` | - | - | Audio transcription |

## Rate Limits (Free Tier)

| Model ID | RPM | RPD | TPM | TPD |
|----------|-----|-----|-----|-----|
| `llama-3.3-70b-versatile` | 30 | 1K | 12K | 100K |
| `llama-3.1-8b-instant` | 30 | 14.4K | 6K | 500K |
| `others` | 30-60 | 1K | 6K-8K | 200K-500K |
