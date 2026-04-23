# Voxtral ASR Optimization Plan (Colab T4)

## Overview

Implement optimizations using `transformers` library on Colab T4 and fix client/server alignment based on the current implementation state. Address Language Collapse, Hallucinations (via Silero VAD), and High Latency (via Streaming logic).

## Tasks

- [x] Research & Cross-check code vs. analysis documents
- [x] Write implementation plan (`voxtral_plan.md`)
- [ ] Get user approval on plan

### Phase 1: VAD Anti-Hallucination Gatekeeper

- [ ] Modify `voxtral_server_transformers.py` to import `silero-vad` via `torch.hub.load`.
- [ ] Implement a pre-check inside the `commit` event block using Silero VAD on the accumulated buffer.
- [ ] If silence is detected strongly, return `{"type": "response.audio_transcript.done", "transcript": ""}` without invoking the GPU.

### Phase 2: Model Optimization & Explicit Language Injection

- [ ] Update `_run_inference_sync` to inject Japanese prompt tokens ahead of `generate()`.
- [ ] Ensure model correctly utilizes `float16` and respects the prompt prefix.
- [ ] Verify Japanese decoding on known "language collapse" files.

### Phase 3: Realtime Text Delta Streaming

- [ ] Import `TextIteratorStreamer` and `threading` in `voxtral_server_transformers.py`.
- [ ] Push `model.generate()` to a sub-thread and iterate over `streamer` to emit `response.audio_transcript.delta` messages over WebSocket.
- [ ] Update client `run_asr.py` loops in `transcription_client` to handle incremental `delta` updates (print to terminal).

### Phase 4: Verification & Benchmarking

- [ ] Measure VRAM and inference response speed after incorporating stream yields.
- [ ] Run full benchmark against silence files and noisy speech files.
