# Audio Analysis: media_148414 — Root Cause Investigation

## Problem

53-second Japanese conversation → only **"Hi, Joseph. I'm sorry."** (deterministic across all runs).

---

## 1. Audio Properties

| Property | Value |
|----------|-------|
| Format | MP3, mono, **8kHz** native SR |
| Duration | 53.36s |
| Bitrate | ~28 kbps |
| RMS | 0.039 |

## 2. Key Finding: ALL Files Are 8kHz

| File | Native SR | Duration | Transcript Length | Status |
|------|-----------|----------|-------------------|--------|
| media_148280 | 8kHz | 80.1s | 167 chars | ✅ JP OK |
| media_148284 | 8kHz | 40.4s | 272 chars | ✅ JP OK |
| media_148393 | 8kHz | 25.6s | 193 chars | ✅ JP OK |
| media_148394 | 8kHz | 31.3s | 168 chars | ✅ JP OK |
| **media_148414** | **8kHz** | **53.4s** | **22 chars** | ❌ **EN hallucination** |
| media_148439 | 8kHz | 34.2s | 181 chars | ✅ JP OK |
| media_148954 | 8kHz | 96.0s | 222 chars | ✅ JP OK |
| media_149291 | 8kHz | 156.6s | 23 chars | ⚠️ Short output |
| media_149733 | 8kHz | 108.6s | 177 chars | ✅ JP OK |

> [!IMPORTANT]
> 8kHz sample rate is NOT the differentiator — other 8kHz files transcribe correctly. The issue is specific to **audio content/characteristics** of this file.

## 3. Energy Analysis

The file has **clear speech ~45/53 seconds** with normal energy levels (-22 to -44 dB). **Not a silence/VAD issue.**

```
 0s   -44 dB · (silence)          30-35s -25 dB ████ (strong speech)
 1-10s -26~-38 dB ██ (speech)     35-44s -22~-27 dB ████ (loud speech)
11-13s -40~-47 dB · (pause)       45-50s -25~-31 dB ██ (speech)
14-24s -28~-37 dB ██ (speech)     51-52s -41~-51 dB · (silence end)
25-27s -40~-47 dB · (pause)
28-29s -26~-32 dB ██ (speech)
```

## 4. Historical Consistency

**Identical result across ALL runs** (18-04 → 23-04): always "Hi, Joseph. I'm sorry." — **deterministic model behavior**, not infrastructure issue.

## 5. Revised Root Cause Hypotheses

### 🔴 H1: Audio Content Characteristics (MOST LIKELY)

- This specific conversation has something the model misinterprets
- Possible: speaker accents, background noise patterns, telephony switching tones, or specific vocal qualities
- The model consistently "hears" an English greeting pattern
- **Test with per-segment inference** to isolate which portion triggers the hallucination

### 🔴 H2: Model Hallucination on Ambiguous Audio

- With `temperature=0`, the model deterministically collapses to a memorized phrase
- "Hi, Joseph. I'm sorry." may be a training data artifact triggered by specific acoustic patterns
- **Test with temperature sampling** to see if alternative decodings emerge

### 🟡 H3: Duration + Content Interaction

- media_149291 (156.6s) also has suspiciously short output (23 chars)
- Longer files with certain content patterns may cause the model to "give up" early
- `max_new_tokens=512` should be sufficient, but worth checking token consumption

## 6. Files Created

All in `d:\VJ\Voxtral\audio\148414\`:

| File | Range | Notes |
|------|-------|-------|
| `segment_00` - `segment_10` | 5s each | 11 WAV segments at 16kHz |
| [full_16khz.wav](file:///d:/VJ/Voxtral/audio/148414/full_16khz.wav) | Full file | Direct 16kHz resample |
| [full_16khz_int16_roundtrip.wav](file:///d:/VJ/Voxtral/audio/148414/full_16khz_int16_roundtrip.wav) | Full file | Simulates server int16 conversion |
| [analysis_report.json](file:///d:/VJ/Voxtral/audio/148414/analysis_report.json) | — | Full data |

## 7. Colab Test Commands

> [!TIP]
> Run **Test 0 (Setup)** exactly once in your Colab notebook before running the other tests.

### Test 0: Common Setup (Run Once)

```python
import os
import torch
import librosa
import numpy as np
from transformers import VoxtralRealtimeForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from mistral_common.tokens.tokenizers.audio import Audio

# 1. 4-bit Quantization logic (from voxtral_baseline.ipynb)
# Crucial for Colab T4 GPUs to avoid Out of Memory errors
quantization_config = None
if torch.cuda.is_available():
    major, _ = torch.cuda.get_device_capability()
    if major < 8:
        print("Turing GPU (T4) detected. Using 4-bit quantization for VRAM safety.")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

# 2. Load Model & Processor
model_id = "mistralai/Voxtral-Mini-4B-Realtime-2602"
model = VoxtralRealtimeForConditionalGeneration.from_pretrained(
    model_id, 
    device_map="auto", 
    torch_dtype=torch.float16,
    quantization_config=quantization_config
)
processor = AutoProcessor.from_pretrained(model_id)

SEGMENTS_DIR = "/content/148414"  # ⚠️ Make sure your segments are uploaded here!
print("Setup complete.")
```

### Test 1: Per-segment inference

```python
# Isolate which 5s chunk causes hallucination
for seg_file in sorted(os.listdir(SEGMENTS_DIR)):
    if not seg_file.endswith('.wav') or 'full' in seg_file:
        continue
        
    fpath = os.path.join(SEGMENTS_DIR, seg_file)
    audio_np, sr = librosa.load(fpath, sr=16000)
    audio_obj = Audio(audio_array=audio_np, sampling_rate=16000, format="wav")
    audio_obj.resample(processor.feature_extractor.sampling_rate)
    
    inputs = processor(text="日本語で書き起こしてください。", audio=audio_obj.audio_array, return_tensors="pt")
    inputs = inputs.to(model.device)
    for k, v in inputs.items():
        if torch.is_floating_point(v): inputs[k] = v.to(model.dtype)
    
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=256, do_sample=False)
        
    transcript = processor.tokenizer.decode(output[0], skip_special_tokens=True)
    prompt_text = "日本語で書き起こしてください。"
    if prompt_text in transcript:
        transcript = transcript.split(prompt_text, 1)[-1].strip()
        
    print(f"{seg_file:40s} → {transcript}")
```

### Test 2: Full file — prompt variations

```python
# Check if prompt triggers English output
audio_np, sr = librosa.load(os.path.join(SEGMENTS_DIR, "full_16khz.wav"), sr=16000)
audio_obj = Audio(audio_array=audio_np, sampling_rate=16000, format="wav")
audio_obj.resample(processor.feature_extractor.sampling_rate)

prompts = [
    "日本語で書き起こしてください。",     # current
    "",                                     # no prompt
    "Transcribe the following audio.",       # English
    "この音声を文字起こししてください。",    # alt JP
]

for prompt in prompts:
    if prompt:
        inputs = processor(text=prompt, audio=audio_obj.audio_array, return_tensors="pt")
    else:
        inputs = processor(audio=audio_obj.audio_array, return_tensors="pt")
        
    inputs = inputs.to(model.device)
    for k, v in inputs.items():
        if torch.is_floating_point(v): inputs[k] = v.to(model.dtype)
        
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=512, do_sample=False)
        
    transcript = processor.tokenizer.decode(output[0], skip_special_tokens=True)
    if prompt and prompt in transcript:
        transcript = transcript.split(prompt, 1)[-1].strip()
        
    print(f"Prompt: {prompt!r:50s} → {transcript[:200]}")
```

### Test 3: Temperature sampling

```python
# Check if alternative decodings exist by forcing sampling
audio_np, sr = librosa.load(os.path.join(SEGMENTS_DIR, "full_16khz.wav"), sr=16000)
audio_obj = Audio(audio_array=audio_np, sampling_rate=16000, format="wav")
audio_obj.resample(processor.feature_extractor.sampling_rate)

inputs = processor(text="日本語で書き起こしてください。", audio=audio_obj.audio_array, return_tensors="pt")
inputs = inputs.to(model.device)
for k, v in inputs.items():
    if torch.is_floating_point(v): inputs[k] = v.to(model.dtype)

for temp in [0.1, 0.3, 0.5, 0.7]:
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=temp)
        
    transcript = processor.tokenizer.decode(output[0], skip_special_tokens=True)
    prompt_text = "日本語で書き起こしてください。"
    if prompt_text in transcript:
        transcript = transcript.split(prompt_text, 1)[-1].strip()
        
    print(f"temp={temp} → {transcript[:200]}")
```

### Test 4: Spectral comparison plot

```python
import matplotlib.pyplot as plt
import requests

# Download a known-good file (you can upload one directly if preferred)
# We will compare the problematic file against another 8kHz file that worked
good_file_path = "/content/media_148280.mp3"
if not os.path.exists(good_file_path):
    print("Please upload media_148280_1767762915627.mp3 to /content/ for comparison.")

try:
    y_bad, _ = librosa.load(os.path.join(SEGMENTS_DIR, "full_16khz.wav"), sr=16000)
    y_good, _ = librosa.load(good_file_path, sr=16000)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    mel_bad = librosa.power_to_db(librosa.feature.melspectrogram(y=y_bad, sr=16000), ref=np.max)
    mel_good = librosa.power_to_db(librosa.feature.melspectrogram(y=y_good, sr=16000), ref=np.max)
    
    librosa.display.specshow(mel_bad, sr=16000, ax=axes[0,0], x_axis='time', y_axis='mel')
    axes[0,0].set_title("BAD: media_148414")
    
    librosa.display.specshow(mel_good, sr=16000, ax=axes[0,1], x_axis='time', y_axis='mel')
    axes[0,1].set_title("GOOD: media_148280")
    
    fft_bad = np.abs(np.fft.rfft(y_bad[:16000*5]))
    fft_good = np.abs(np.fft.rfft(y_good[:16000*5]))
    
    freqs = np.fft.rfftfreq(16000*5, d=1/16000)
    axes[1,0].semilogy(freqs, fft_bad)
    axes[1,0].set_title("BAD: FFT (first 5s)")
    axes[1,1].semilogy(freqs, fft_good)
    axes[1,1].set_title("GOOD: FFT (first 5s)")
    
    plt.tight_layout()
    plt.savefig("/content/spectral_comparison.png", dpi=150)
    plt.show()
except Exception as e:
    print(f"Make sure you uploaded both files! Error: {e}")
```

### Test 5: Pre-emphasis filter

```python
import scipy.signal

audio_np, _ = librosa.load(os.path.join(SEGMENTS_DIR, "full_16khz.wav"), sr=16000)
# Simple acoustic fix (boost high frequencies)
audio_preemph = np.append(audio_np[0], audio_np[1:] - 0.97 * audio_np[:-1])

audio_obj = Audio(audio_array=audio_preemph, sampling_rate=16000, format="wav")
audio_obj.resample(processor.feature_extractor.sampling_rate)

inputs = processor(text="日本語で書き起こしてください。", audio=audio_obj.audio_array, return_tensors="pt")
inputs = inputs.to(model.device)
for k, v in inputs.items():
    if torch.is_floating_point(v): inputs[k] = v.to(model.dtype)
    
with torch.inference_mode():
    output = model.generate(**inputs, max_new_tokens=512, do_sample=False)
    
transcript = processor.tokenizer.decode(output[0], skip_special_tokens=True)
prompt_text = "日本語で書き起こしてください。"
if prompt_text in transcript:
    transcript = transcript.split(prompt_text, 1)[-1].strip()
    
print(f"Pre-emphasis result: {transcript}")
```

## 8. Recommended Execution Order

1. **Test 0** (Setup model) — Must run first!
2. **Test 1** (per-segment) — Isolate which 5s chunk causes hallucination
3. **Test 2** (prompt variations) — Check if prompt triggers English output
4. **Test 3** (temperature) — Check if alternative decodings exist
5. **Test 5** (pre-emphasis) — Test simple acoustic fix
6. **Test 4** (spectral comparison) — Visualize difference vs. good file
