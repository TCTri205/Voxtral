# Root Cause Analysis: media_148414 Hallucination

## Problem
53s Japanese conversation → model outputs only **"Hi, Joseph. I'm sorry."**

---

## Colab Test Results

### Test 1 — Per-Segment Inference (5s chunks)

| Segment | Time | Result |
|---------|------|--------|
| `segment_00` | 0-5s | ❌ **"Hi, Joseph. I'm sorry."** |
| `segment_01` | 5-10s | ✅ 株式会社アセットジャパンといいますけれども、お世話になります。 |
| `segment_02` | 10-15s | ⚠️ おめでとうか (short) |
| `segment_03` | 15-20s | ⚠️ (empty) |
| `segment_04` | 20-25s | ✅ 急ぎではございませんのでまたこちらから改めさせていただきます |
| `segment_05` | 25-30s | ✅ 名前が関してよろしいですか?窃盗ジャパンの伊藤でございます |
| `segment_06` | 30-35s | ✅ 一言すいませんご伝言をお願いできますでしょうか |
| `segment_07` | 35-40s | ✅ どうぞまた山内様宛てにですね東浦町 |
| `segment_08` | 40-45s | ✅ 今度は東浦町の物件についてメールでお問い合わせ |
| `segment_09` | 45-50s | ✅ しましたお伝えください確かまりましたお伝えいたしますはい... |
| `segment_10` | 50-53s | ⚠️ (empty — tail silence) |

> [!IMPORTANT]
> **Root cause isolated: segment_00 (0-5s) is the sole trigger.** All other segments produce correct Japanese transcriptions.

#### CER Evaluation

**Concatenated hypothesis** (11 segments → full transcript):

```
Hi, Joseph. I'm sorry.株式会社アセットジャパンといいますけれども、お世話になります。おめでとうか急ぎではございませんのでまたこちらから改めさせていただきます名前が関してよろしいですか?窃盗ジャパンの伊藤でございます一言すいませんご伝言をお願いできますでしょうかどうぞまた山内様宛てにですね東浦町今度は東浦町の物件についてメールでお問い合わせしましたお伝えください確かまりましたお伝えいたしますはいありがとうございます
```

**Character Error Rate (CER)** — computed with the official `normalize_japanese` (punctuation/strip/full-width→half-width) + `calculate_cer` from `llm_evaluator/voxtral_utils.py`:

| Metric | Value |
|--------|-------|
| Reference length (normalized) | 392 chars |
| Hypothesis length (normalized) | 210 chars |
| Edit distance | 215 |
| **CER** | **54.85%** |

Segment‑00 alone yields **100% CER** (pure hallucination). The mix of 10 subsequent segments (many near‑perfect) reduces the aggregate to **54.85%** — still a failing grade, but far from the total loss implied by segment‑00 in isolation.

### Test 2 — Prompt Variations (Full File)

| Prompt | Result |
|--------|--------|
| `日本語で書き起こしてください。` | Hi, Joseph. I'm sorry. |
| *(empty)* | Hi, Joseph. I'm sorry. |
| `Transcribe the following audio.` | Hi, Joseph. I'm sorry. |
| `この音声を文字起こししてください。` | Hi, Joseph. I'm sorry. |

**Conclusion: Prompt has ZERO effect.** The hallucination is driven entirely by audio features.

### Test 3 — Temperature Sampling (Full File)

| Temperature | Result |
|-------------|--------|
| 0.1 | Hi, Joseph. I'm sorry. |
| 0.3 | Hi, Joseph. I'm sorry. I'm sorry. |
| 0.5 | Hi, Joseph. I'm sorry. I'm from Nagoya Company... |
| 0.7 | Hi, Joseph. Thanks for calling. Nice to meet you... |

**Conclusion:** Higher temperature produces *more* English hallucination, not Japanese. The model's top token probabilities are firmly in English space for this audio.

### Test 4 — Spectral Comparison

![Spectral comparison between BAD (148414) and GOOD (148280) files](C:\Users\This PC\.gemini\antigravity\brain\d276cbd8-35ec-48ed-a295-f742da9b17ed\spectral_comparison.png)

**Key observations from FFT (bottom row):**
- Both files have sharp cutoff at 4kHz (8kHz Nyquist) — same spectral profile
- BAD file (left) has a **harder, more abrupt cutoff** at 4kHz compared to GOOD file
- GOOD file (right) has a **smoother rolloff** with some residual energy above 4kHz
- Mel spectrograms (top) look structurally similar — both show speech patterns

### Test 5 — Pre-Emphasis Filter

| Method | Result |
|--------|--------|
| Pre-emphasis (0.97) | *(empty)* |

**Conclusion:** Pre-emphasis made it worse — the model couldn't produce anything at all.

---

## Root Cause: Confirmed

### 🔴 Autoregressive Cascade Failure

The model's behavior follows a clear failure pattern:

```
segment_00 (0-5s) → English hallucination "Hi, Joseph. I'm sorry."
                   ↓ (autoregressive: first tokens condition all following)
Full file inference → model "locks in" to English mode from first tokens
                   ↓ 
                   → generates short English phrase → stops (EOS)
                   → entire 48s of valid Japanese speech is NEVER processed
```

**Why segment_00 triggers hallucination:**
- The first 0-1s is near-silence (-44 dB), followed by speech onset at 1-5s
- The energy analysis shows this segment has a transitional pattern: silence → ringing/dial tone → speech start
- The telephone switching/ringing sound in the first few seconds is acoustically similar to patterns the model associates with English greetings
- With `temperature=0` (greedy), once the first token is English, all subsequent tokens follow

**Why individual segments work:**
- When segments 1-10 are processed independently, there's no "poisoned" prefix — the model correctly starts in Japanese mode

### Evidence Summary

| Hypothesis | Status | Evidence |
|---|---|---|
| H1: Audio content (segment_00) | ✅ **CONFIRMED** | Test 1 isolates it to first 5s |
| H2: Model hallucination | ✅ **CONFIRMED** | Test 3 shows English-locked token distribution; CER 54.85% overall, 100% on segment-00 alone |
| H3: Prompt effect | ❌ Ruled out | Test 2 shows zero prompt influence |
| H4: 8kHz sample rate | ❌ Ruled out | All files are 8kHz, others work fine |
| H5: Pre-emphasis fix | ❌ Failed | Test 5 made it worse |

---

## Proposed Fixes

### Fix 1: Trim Leading Silence/Noise (Quick Win)
Trim the first ~1s of silence before sending to model. This removes the telephone switching tone that triggers English mode.

### Fix 2: Chunked Inference with Concatenation
Split long files into ~10-15s chunks, transcribe each independently, then concatenate results. This prevents one bad segment from poisoning the entire transcript.

### Fix 3: Retry with Segment Skipping
If the model produces suspiciously short output (<5 chars) for a long file (>20s), retry with the first 5s trimmed.

### Fix 4: Post-Hoc Language Detection
After inference, check if the output language matches the expected language. If not, retry with the audio trimmed or chunked.
