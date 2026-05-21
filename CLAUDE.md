# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voxtral ASR Server - A speech-to-text engine powered by Mistral's Voxtral models with advanced VAD (Voice Activity Detection), hallucination detection, and Japanese language collapse recovery.

## Architecture

The system has two main ASR engines:

1. **Voxtral Transformers Server** (`voxtral_server_transformers.py`) - Local server using Mistral's Voxtral model with:
   - Silero VAD for speech detection and trimming
   - Chunked inference for long audio (>15s) with overlap handling
   - Japanese language collapse detection and recovery
   - Hallucination guardrails with multi-temperature retry

2. **Javis Engine** - External WebSocket-based ASR service (see `README_JAVIS.md`)

### Key Pipeline Stages
1. **Preprocessing**: DC offset removal, 80Hz high-pass filter, adaptive RMS normalization
2. **VAD Trimming**: Speech detection with asymmetric padding (300ms left, 350ms right)
3. **Chunked Inference**: VAD-aware chunking with 15s max, 0.5s overlap handling
4. **Recovery**: Sub-chunk splitting and language collapse recovery for suspicious transcripts
5. **Guardrails**: Hallucination detection with optional retry at T=0.2

## Common Commands

```bash
# Start the Voxtral server (CUDA)
python voxtral_server_transformers.py --model mistralai/Voxtral-Mini-4B-Realtime-2602 --port 8000

# Start with 4-bit quantization (recommended for T4 GPU)
python voxtral_server_transformers.py --model mistralai/Voxtral-Mini-4B-Realtime-2602 --load-in-4bit

# Run inference on a file (if test script exists)
python generate_test_samples.py
```

## Configuration Constants (voxtral_server_transformers.py)

Key tunables for Japanese telephony business conversations:
- `VAD_THRESHOLD = 0.45` - Lowered to capture quiet speech
- `VAD_PADDING_LEFT_MS = 300` / `VAD_PADDING_RIGHT_MS = 350` - Asymmetric padding
- `LANG_COLLAPSE_JP_RATIO = 0.55` - Japanese character ratio threshold for collapse detection
- `CHUNK_LIMIT_SEC = 15.0` / `CHUNK_OVERLAP_SEC = 0.5` - Chunk sizing
- `RETRY_TEMPERATURE = 0.2` - Fixed retry temperature for hallucination recovery

## Output Structure

- `results/` - ASR results with transcripts and metrics
- `benchmarks/` - Benchmark JSON files with RTF and accuracy metrics
- `results_javis/` - Separate results for Javis engine (not Voxtral)
- `llm_evaluator/` - Hallucination evaluation module using LLM