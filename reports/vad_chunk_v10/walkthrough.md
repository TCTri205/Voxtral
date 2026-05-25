# Walkthrough: CER Enhancement & RTF Optimization (V10)

This document provides a summary of the implementation details for the CER enhancement and RTF optimization plan (v10) applied to the Voxtral project.

## Completed Tasks & Code Modifications

### 1. RTF Optimization: Efficient N-gram Loop Detection
We optimized `RepetitionStoppingCriteria` in [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py) to check for loops every 5 generation steps instead of checking at every single token. This reduces token decoding overhead by 80% with negligible delay in detection.

Additionally, `max_new_tokens` was reduced from `512` to `256` for individual chunk generation inside `_run_inference_for_chunk()`, protecting the server against runaway loop generation on noisy inputs.

### 2. PyTorch Native SDPA Activation
In `load_voxtral_model()`, we added native PyTorch SDPA (Scaled Dot-Product Attention) activation when the model is loaded on a GPU (`device == "cuda"`). This is done by dynamically setting `"attn_implementation": "sdpa"` in `from_pretrained()` kwargs.

### 3. Dynamic Domain Glossary & CER Tracking
- We added `_load_domain_glossary()` and `_apply_domain_glossary()` helpers to load rules dynamically from the path specified by the `ASR_GLOSSARY_PATH` environment variable. A fallback glossary (`DEFAULT_GLOSSARY`) is used if `ASR_USE_DEFAULT_GLOSSARY=true` is set.
- We updated the inference loop inside `_run_inference_sync()` to:
  1. Hold the original model output in `raw_transcript`.
  2. Apply the domain glossary onto the transcript to produce the final `transcript`.
  3. Propagate both `transcript` and `raw_transcript` in the `_inference_result` payload.
- Updated the WebSocket server handler in [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py) to send `"raw_transcript"` to the client within the `"response.audio_transcript.done"` message.

### 4. Client-side Propagation
We modified the WebSocket client in [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py) to extract `raw_transcript` from the payload and propagate it to the output metrics JSON.

### 5. CER Metrics Evaluation
In [evaluate_metrics.py](file:///d:/VJ/Voxtral/evaluate_metrics.py), we updated the metrics calculation block to compute and report both **Raw CER** (on the model's raw output) and **Adjusted CER** (on the glossary-corrected output) in parallel. Both metrics are now saved in the results JSON and printed side-by-side in the markdown reports.

### 6. LLM Evaluator Prompt Enhancement
We clarified the distinction between ASR substitution errors and hallucination/insertion errors in `SYSTEM_PROMPT_BASE` inside [llm_evaluator/prompt_builder.py](file:///d:/VJ/Voxtral/llm_evaluator/prompt_builder.py). The LLM evaluator is now instructed to classify phonetic substitution errors as `none` and only count actual silence-filling or out-of-ground-truth phrases as insertions/hallucinations.
