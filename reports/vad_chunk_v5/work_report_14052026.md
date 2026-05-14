# Voxtral ASR Optimization Report (V5/V6) - 14/05/2026

## 1. Executive Summary
Today's optimization focused on resolving high Character Error Rates (CER) and persistent "Insertion" hallucinations (e.g., hallucinating conversational fillers like "お茶" on noise) identified in previous versions.

**Key Achievements:**
- **CER Reduction:** Improved from **48.97% (v1)** to **40.27% (v6)**.
- **Noise Immunity:** Achieved **0.000 HRS** (Hallucination Rate on Silence). The system no longer produces text for silence or stochastic noise.
- **Stability:** Fixed a critical RTF regression (from 13.0 back to ~2.0) and corrected false-positive loop detections for Japanese grammatical suffixes.

## 2. Technical Changes (V5/V6 Architecture)

### VAD & Chunking Parameters
| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| `VAD_THRESHOLD` | **0.65** | Increased from 0.55 to filter out environmental noise. |
| `VAD_SEGMENT_SILENCE_MS` | **1000ms** | Balanced context retention vs. loop prevention. |
| `VAD_CHUNK_PADDING_MS` | **200ms** | Minimized noise capture at segment edges. |

### Active Guardrails
- **RepetitionStoppingCriteria:** Real-time token monitoring to kill infinite loops (e.g., "ですですです...") early.
- **N-Gram Loop Detector (v14.3):** Added an allowlist for ~25 common Japanese business suffixes (`ます`, `です`, `ります`, etc.) to prevent false-positive hallucination flags on legitimate speech.
- **Phase 3 Recovery:** Enabled environmental variable `VOXTRAL_RETRY_HALLUCINATION` to allow multi-temperature retries for suspicious segments.

## 3. Benchmark Results Analysis (v6)

### Aggregate Metrics
- **Average CER:** 40.27%
- **Average Inference RTF:** 2.042
- **HRS (Silence/Noise):** 0.000 CPM (Total Success)

### LLM Evaluation Insights (Groq llama-3.3-70b)
The LLM evaluator identifies two primary remaining error categories:

1. **Insertion Hallucinations (Medium Severity):**
   - **Pattern:** Model inserts "Greeting" phrases (e.g., `お茶になっております`, `お待たせいたしました`) when audio is slightly noisy or unclear.
   - **Root Cause:** The 4B model has a high prior for these phrases and "over-guesses" them during low signal-to-noise ratio (SNR) segments.

2. **Entity Replacement (High Severity):**
   - **Example:** `中央清算管理課` (Central Clearing Dept) → `先生管理課` (Teacher Management Dept).
   - **Root Cause:** Acoustic misrecognition of specific proper nouns and business entities.

## 4. RTF Regression & Resolution
- **Issue:** RTF spiked to **13.0** during v5 testing.
- **Cause:** `ENABLE_RETRY_HALLUCINATION` was forced `True`, and an overly sensitive loop detector triggered 3x inference runs (Temperature 0.0, 0.3, 0.5) for almost every file due to the word `ます`.
- **Fix (v14.2/v14.3):** Reverted retry to opt-in, widened the n-gram threshold (n=3+), and implemented the Japanese grammatical allowlist. RTF returned to **~2.0**.

## 5. Next Steps
- [ ] **Beam Search Tuning:** Increase beam size or adjust `repetition_penalty` to discourage "guessed" conversational fillers.
- [ ] **Preprocessing Polish:** Investigate if the Soft Noise Gate in `_preprocess_audio` can be more aggressive without clipping valid speech.
- [ ] **Entity Post-Processing:** Potential use of a fuzzy-match dictionary for common client company names to fix "Content Replacement" errors.

---
**Status:** Baseline Stabilized. Ready for Phase 2 (Accuracy Deep-Dive).
**Server Version:** `2026-05-14.3`
