import os
import json
import base64
import asyncio
import uuid
import time
import math
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import VoxtralRealtimeForConditionalGeneration, AutoProcessor, TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
from mistral_common.tokens.tokenizers.audio import Audio
import argparse
import librosa # Added for server-side file loading
import threading
from scipy import signal

app = FastAPI()

# Global variables for model and processor
model = None
processor = None
model_id_global = None

# VAD global state
vad_model = None
vad_utils = None

# Chunked inference constants
CHUNK_LIMIT_SEC = 15.0
CHUNK_OVERLAP_SEC = 1.0
VAD_PADDING_MS = 300  # Tightened from 400ms to reduce trailing silence hallucinations

# Silero VAD configuration (optimized for Japanese business conversations)
VAD_THRESHOLD = 0.70  # Increased from 0.65 to be more selective in noisy telephony audio
VAD_MIN_SPEECH_DURATION_MS = 400
VAD_MIN_SILENCE_DURATION_MS = 100

# Online VAD-Aware Chunking config
VAD_SEGMENT_SILENCE_MS = 700  # Tightened from 1000 to break chunks earlier
VAD_CHUNK_PADDING_MS = 200     # Reverted to v2 padding to avoid capturing noise

# Hallucination guardrails config
# Enabled for v7 to tackle tail-end repetitions
ENABLE_RETRY_HALLUCINATION = True
RETRY_TEMPERATURE = 0.2

# Language Collapse Auto-Recovery config
LANG_COLLAPSE_ASCII_RATIO = 0.7
LANG_COLLAPSE_MIN_CHARS = 5
LANG_COLLAPSE_CONTEXT_SEC = 5.0
LANG_COLLAPSE_MAX_RETRY_CHUNKS = 3
ENABLE_LANG_COLLAPSE_RECOVERY = True
ENABLE_PREPROCESSING = True

# ---------------------------------------------------------------------------
# Server revision fingerprint
# ---------------------------------------------------------------------------
_SERVER_VERSION = "2026-05-14.4"

def _vad_config_metadata() -> dict:
    return {
        "VAD_THRESHOLD": VAD_THRESHOLD,
        "VAD_PADDING_MS": VAD_PADDING_MS,
        "VAD_MIN_SPEECH_DURATION_MS": VAD_MIN_SPEECH_DURATION_MS,
        "VAD_MIN_SILENCE_DURATION_MS": VAD_MIN_SILENCE_DURATION_MS,
        "VAD_SEGMENT_SILENCE_MS": VAD_SEGMENT_SILENCE_MS,
        "VAD_CHUNK_PADDING_MS": VAD_CHUNK_PADDING_MS,
        "CHUNK_LIMIT_SEC": CHUNK_LIMIT_SEC,
        "CHUNK_OVERLAP_SEC": CHUNK_OVERLAP_SEC,
        "LANG_COLLAPSE_ASCII_RATIO": LANG_COLLAPSE_ASCII_RATIO,
        "LANG_COLLAPSE_RECOVERY": ENABLE_LANG_COLLAPSE_RECOVERY,
        "PREPROCESSING_ENABLED": ENABLE_PREPROCESSING,
        "_SERVER_VERSION": _SERVER_VERSION,
    }


def _inference_result(transcript: str, vad_result: dict | None = None, lang_collapse_retries: list | None = None) -> dict:
    return {
        "transcript": transcript,
        "vad_config": _vad_config_metadata(),
        "vad_result": vad_result or {},
        "lang_collapse_retries": lang_collapse_retries or [],
    }


def _detect_language_collapse(transcript: str) -> dict:
    """
    Detect if the transcript is likely a language collapse (hallucinated English).
    Uses the ratio of ASCII alphabetic characters to total non-whitespace characters.
    """
    text = transcript.strip()
    if len(text) == 0:
        return {"is_collapsed": True, "ascii_ratio": 0.0, "reason": "empty_transcript"}
    if len(text) < LANG_COLLAPSE_MIN_CHARS:
        return {"is_collapsed": False, "ascii_ratio": 0.0, "reason": "too_short"}
    
    non_ws = [c for c in text if not c.isspace()]
    if not non_ws:
        return {"is_collapsed": False, "ascii_ratio": 0.0, "reason": "empty"}
    
    ascii_alpha = sum(1 for c in non_ws if c.isascii() and c.isalpha())
    ratio = ascii_alpha / len(non_ws)
    
    return {
        "is_collapsed": ratio > LANG_COLLAPSE_ASCII_RATIO,
        "ascii_ratio": round(ratio, 3),
        "reason": f"ascii_ratio={ratio:.1%}" if ratio > LANG_COLLAPSE_ASCII_RATIO else "ok",
    }


def _preprocess_audio(audio_np: np.ndarray, conn_id: str, sample_rate: int = 16000) -> np.ndarray:
    """
    Perform audio preprocessing to improve ASR quality.
    - DC Offset Removal: Centers the signal at zero.
    - RMS Normalization: Scales the signal to target RMS level (-20dBFS).
    - Gain Clamping: Limits maximum gain to avoid over-amplifying noise.
    - Soft Noise Gate: Attenuates near-silent segments.
    """
    if not ENABLE_PREPROCESSING:
        return audio_np

    t0 = time.time()
    
    # 1. DC Offset Removal
    audio_np = audio_np - np.mean(audio_np)
    
    # 2. High-Pass Filter (80Hz) to remove low-frequency rumble
    try:
        sos = signal.butter(4, 80, 'hp', fs=sample_rate, output='sos')
        audio_np = signal.sosfilt(sos, audio_np)
    except Exception as e:
        _slog(conn_id, f"Preprocessing: HPF failed: {e}")

    # 3. RMS Calculation
    rms = np.sqrt(np.mean(audio_np**2))
    
    # 4. Soft Noise Gate (-50dBFS threshold)
    noise_gate_threshold = 10**(-50/20) # ~0.00316
    if rms < noise_gate_threshold:
        # Near silent: attenuate further to help VAD ignore it
        audio_np = audio_np * 0.1
        _slog(conn_id, f"Preprocessing: Noise gate active (RMS={20*np.log10(rms+1e-9):.1f}dBFS)")
        return audio_np

    # 5. RMS Normalization (Target -20dBFS = 0.1)
    target_rms = 10**(-20/20) # 0.1
    gain = target_rms / (rms + 1e-9)
    
    # 6. Gain Clamping (Max 10x / 20dB)
    clamped_gain = min(gain, 10.0)
    audio_np = audio_np * clamped_gain
    
    # Final safety clip
    audio_np = np.clip(audio_np, -1.0, 1.0)
    
    _slog(conn_id, f"Preprocessing: HPF(80Hz) + RMS Norm (gain={clamped_gain:.2f}x, final_rms={20*np.log10(np.sqrt(np.mean(audio_np**2))+1e-9):.1f}dBFS) in {time.time()-t0:.3f}s")
        
    return audio_np.astype(np.float32)


def _server_fingerprint() -> str:
    """Return a short identifier for the running script revision."""
    script = os.path.abspath(__file__)
    try:
        import subprocess
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(script),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return f"git:{sha}  version:{_SERVER_VERSION}  path:{script}"
    except Exception:
        import hashlib
        try:
            with open(script, "rb") as fh:
                h = hashlib.sha1(fh.read()).hexdigest()[:8]
            return f"file-hash:{h}  version:{_SERVER_VERSION}  path:{script}"
        except Exception:
            return f"version:{_SERVER_VERSION}  path:{script}"


def _slog(conn_id: str, msg: str):
    """Structured server log with connection ID and wall-clock timestamp."""
    ts = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{ts}][{conn_id}] {msg}", flush=True)


async def _safe_send_text(websocket: WebSocket, text: str, conn_id: str):
    """Safely send text over websocket, catching disconnects."""
    try:
        await websocket.send_text(text)
        return True
    except (WebSocketDisconnect, RuntimeError) as e:
        # RuntimeError: Cannot call "send" once a close message has been sent.
        _slog(conn_id, f"send_failed (connection closed): {type(e).__name__}")
        return False


def _trim_silence_with_vad(audio_np: np.ndarray, sample_rate: int = 16000):
    """
    Use Silero VAD to find speech segments and trim leading/trailing silence.

    Args:
        audio_np: float32 numpy array of audio samples (normalized to [-1, 1])
        sample_rate: Sample rate (default 16kHz)

    Returns:
        trimmed_audio: Audio array trimmed to speech segments with padding
        debug_info: Dict with original_duration, trimmed_duration, speech_detected
    """
    if vad_model is None or vad_utils is None:
        # VAD not loaded, return original audio
        return audio_np, {"original_duration": len(audio_np)/sample_rate, "trimmed_duration": len(audio_np)/sample_rate, "speech_detected": True, "vad_error": "VAD not loaded"}

    try:
        original_duration = len(audio_np) / sample_rate
        audio_tensor = torch.from_numpy(audio_np).to(torch.float32)
        get_speech_timestamps = vad_utils[0]

        # Get speech timestamps with configured thresholds
        speech_timestamps = get_speech_timestamps(
            audio_tensor, 
            vad_model, 
            sampling_rate=sample_rate,
            threshold=VAD_THRESHOLD,
            min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
            min_silence_duration_ms=VAD_MIN_SILENCE_DURATION_MS,
        )

        if not speech_timestamps:
            # No speech detected
            return audio_np, {"original_duration": original_duration, "trimmed_duration": original_duration, "speech_detected": False}

        # Find the first and last speech segments
        first_start = speech_timestamps[0]['start']
        last_end = speech_timestamps[-1]['end']

        # Convert sample indices to time (seconds)
        first_start_sec = first_start / sample_rate
        last_end_sec = last_end / sample_rate

        # Apply padding (convert ms to samples)
        padding_samples = int((VAD_PADDING_MS / 1000.0) * sample_rate)
        start_sample = max(0, first_start - padding_samples)
        end_sample = min(len(audio_np), last_end + padding_samples)

        # Trim audio
        trimmed_audio = audio_np[start_sample:end_sample]
        trimmed_duration = len(trimmed_audio) / sample_rate

        debug_info = {
            "original_duration": original_duration,
            "trimmed_duration": trimmed_duration,
            "speech_detected": True,
            "first_speech_start_sec": first_start_sec,
            "last_speech_end_sec": last_end_sec,
            "num_segments": len(speech_timestamps),
            "vad_threshold": VAD_THRESHOLD,
            "min_speech_duration_ms": VAD_MIN_SPEECH_DURATION_MS,
        }

        return trimmed_audio, debug_info

    except Exception as e:
        # On error, return original audio
        return audio_np, {"original_duration": len(audio_np)/sample_rate, "trimmed_duration": len(audio_np)/sample_rate, "speech_detected": True, "vad_error": str(e)}


def _create_vad_aware_chunks(audio_np: np.ndarray, speech_timestamps: list, sample_rate: int = 16000, 
                             max_chunk_sec: float = CHUNK_LIMIT_SEC, 
                             padding_ms: int = VAD_CHUNK_PADDING_MS) -> list:
    """
    Group VAD speech segments into chunks <= max_chunk_sec.
    
    Args:
        audio_np: The audio numpy array
        speech_timestamps: List of dicts with 'start' and 'end' sample indices
        sample_rate: Audio sampling rate
        max_chunk_sec: Maximum duration of a chunk in seconds
        padding_ms: Padding to add around chunks
        
    Returns:
        List of dicts containing 'audio_np', 'start_sec', 'end_sec', 'segments_count'
    """
    if not speech_timestamps:
        return []
        
    chunks = []
    current_chunk_segments = [speech_timestamps[0]]
    current_chunk_start = speech_timestamps[0]['start']
    current_chunk_end = speech_timestamps[0]['end']
    
    padding_samples = int((padding_ms / 1000.0) * sample_rate)
    max_chunk_samples = int(max_chunk_sec * sample_rate)
    
    for i in range(1, len(speech_timestamps)):
        segment = speech_timestamps[i]
        
        # Calculate potential new chunk size if we add this segment
        # (including the silence gap between current_chunk_end and segment['start'])
        potential_chunk_end = segment['end']
        potential_chunk_size = potential_chunk_end - current_chunk_start
        
        if potential_chunk_size <= max_chunk_samples:
            # Segment fits in current chunk
            current_chunk_end = segment['end']
            current_chunk_segments.append(segment)
        else:
            # Add padding and finalize current chunk
            start_idx = max(0, current_chunk_start - padding_samples)
            end_idx = min(len(audio_np), current_chunk_end + padding_samples)
            
            chunk_audio = audio_np[start_idx:end_idx]
            
            # Sub-chunking if a single segment (or a previously started chunk) is somehow longer than max_chunk_sec
            if len(chunk_audio) > max_chunk_samples:
                # Split evenly with consistent overlap between chunks
                chunk_duration = len(chunk_audio) / sample_rate
                overlap_sec = CHUNK_OVERLAP_SEC

                # Calculate number of even chunks needed
                n_chunks = max(2, math.ceil(chunk_duration / (max_chunk_sec - overlap_sec * 0.5)))

                # Calculate effective step to distribute chunks evenly
                effective_duration = chunk_duration - overlap_sec
                step = effective_duration / (n_chunks - 1) if n_chunks > 1 else effective_duration
                step_samples = int(step * sample_rate)
                overlap_samples = int(overlap_sec * sample_rate)

                for i in range(n_chunks):
                    sub_pos = int(i * step_samples)
                    sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
                    sub_audio = chunk_audio[sub_pos:sub_end]

                    actual_start_sec = (start_idx + sub_pos) / sample_rate
                    actual_end_sec = (start_idx + sub_end) / sample_rate

                    chunks.append({
                        "audio_np": sub_audio,
                        "start_sec": actual_start_sec,
                        "end_sec": actual_end_sec,
                        "segments_count": len(current_chunk_segments) if i == 0 else 0,
                        "is_sub_chunk": True,
                    })
            else:
                chunks.append({
                    "audio_np": chunk_audio,
                    "start_sec": start_idx / sample_rate,
                    "end_sec": end_idx / sample_rate,
                    "segments_count": len(current_chunk_segments),
                    "is_sub_chunk": False,
                })
            
            # Start new chunk
            current_chunk_start = segment['start']
            current_chunk_end = segment['end']
            current_chunk_segments = [segment]
            
    # Process final chunk
    start_idx = max(0, current_chunk_start - padding_samples)
    end_idx = min(len(audio_np), current_chunk_end + padding_samples)
    chunk_audio = audio_np[start_idx:end_idx]
    
    if len(chunk_audio) > max_chunk_samples:
        # Split evenly with consistent overlap between chunks
        chunk_duration = len(chunk_audio) / sample_rate
        overlap_sec = CHUNK_OVERLAP_SEC

        # Calculate number of even chunks needed
        n_chunks = max(2, math.ceil(chunk_duration / (max_chunk_sec - overlap_sec * 0.5)))

        # Calculate effective step to distribute chunks evenly
        effective_duration = chunk_duration - overlap_sec
        step = effective_duration / (n_chunks - 1) if n_chunks > 1 else effective_duration
        step_samples = int(step * sample_rate)

        for i in range(n_chunks):
            sub_pos = int(i * step_samples)
            sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
            sub_audio = chunk_audio[sub_pos:sub_end]

            chunks.append({
                "audio_np": sub_audio,
                "start_sec": (start_idx + sub_pos) / sample_rate,
                "end_sec": (start_idx + sub_end) / sample_rate,
                "segments_count": len(current_chunk_segments) if i == 0 else 0,
                "is_sub_chunk": True,
            })
    else:
        chunks.append({
            "audio_np": chunk_audio,
            "start_sec": start_idx / sample_rate,
            "end_sec": end_idx / sample_rate,
            "segments_count": len(current_chunk_segments),
            "is_sub_chunk": False,
        })
        
    return chunks


class RepetitionStoppingCriteria(StoppingCriteria):
    """Stopping criteria that interrupts generation if it detects n-gram loops."""
    def __init__(self, tokenizer, threshold=3, n_range=(3, 4, 5)):
        self.tokenizer = tokenizer
        self.threshold = threshold
        self.n_range = n_range

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        # Decode the last 50 tokens to check for loops
        last_tokens = input_ids[0, -50:]
        text = self.tokenizer.decode(last_tokens, skip_special_tokens=True)
        # Remove whitespace
        clean_text = "".join(text.split())
        
        if len(clean_text) < 10:
            return False

        # Stricter detection for longer n-grams
        for n in self.n_range:
            # Check for repeating n-grams at the very end of the text
            # Threshold 2 for n >= 4 to catch phrases earlier
            current_threshold = 2 if n >= 4 else self.threshold
            
            if len(clean_text) < n * current_threshold:
                continue
            
            tail = clean_text[-(n * current_threshold):]
            gram = tail[-n:]
            if gram * current_threshold == tail:
                return True
        return False


def _run_inference_for_chunk(audio_np: np.ndarray, session_config: dict, conn_id: str, on_delta=None) -> tuple:
    """
    Run inference for a single chunk of audio.
    Internal helper used by _run_inference_sync for chunked processing.
    """
    t0 = time.time()

    # Build an Audio object the way the official example shows
    audio_obj = Audio(
        audio_array=audio_np,
        sampling_rate=16_000,
        format="wav",
    )
    # Resample to the rate the feature extractor expects (usually 16kHz, but future-proof)
    audio_obj.resample(processor.feature_extractor.sampling_rate)

    # Language hint: Client can specify language via session config.
    # NOTE: Voxtral model does NOT support language hints via text prefix.
    # The language parameter is kept for logging/debugging purposes only.
    language = session_config.get("language", "ja")

    # Run inference with audio only - no text prefix
    inputs = processor(
        audio=audio_obj.audio_array,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)
    for k, v in inputs.items():
        if torch.is_floating_point(v):
            inputs[k] = v.to(model.dtype)

    temperature = float(session_config.get("temperature", 0.0))
    do_sample = temperature > 0.0

    # Setup streamer and stopping criteria
    streamer = TextIteratorStreamer(processor.tokenizer, skip_special_tokens=True, skip_prompt=True)
    stopping_criteria = StoppingCriteriaList([
        RepetitionStoppingCriteria(processor.tokenizer, threshold=3)
    ])

    generation_kwargs = dict(
        **inputs,
        max_new_tokens=512,
        do_sample=do_sample,
        temperature=temperature if do_sample else None,
        streamer=streamer,
        stopping_criteria=stopping_criteria,
    )

    # Run generation in a separate thread because streamer.iterator is blocking
    error_container = []

    def safe_generate():
        try:
            with torch.inference_mode():
                model.generate(**generation_kwargs)
        except Exception as e:
            error_container.append(e)
            # End the streamer so the main loop doesn't hang
            streamer.end()

    thread = threading.Thread(target=safe_generate)
    thread.start()

    # Collect tokens and call on_delta callback
    full_transcript = ""
    for new_text in streamer:
        if on_delta:
            on_delta(new_text)
        full_transcript += new_text

    # Check for errors in the thread
    if error_container:
        e = error_container[0]
        _slog(conn_id, f"inference_thread_error: {e}")
        raise e

    transcript = full_transcript.strip()

    elapsed = time.time() - t0
    return transcript, elapsed


def _detect_ngram_loops(text: str, n_range=(3, 4, 5), threshold=4) -> list:
    """
    Detect if any n-gram (character-level for Japanese) repeats more than threshold times.
    Excludes common Japanese grammatical suffixes that are legitimately high-frequency.
    """
    # Common Japanese grammatical endings that appear frequently in normal business speech
    # These are NOT hallucinations even if they repeat many times.
    JAPANESE_COMMON_GRAMS = {
        # 2-char
        "ます", "です", "した", "して", "ない", "ので", "いる", "ある", "から", "けど",
        "には", "ては", "では", "とは", "から", "より", "まで", "でも",
        # 3-char
        "ります", "います", "えます", "きます", "します", "ません", "でした", "ました",
        "ください", "しては", "におい", "について", "ありがと",
        # 4-char
        "ありがとう", "おります", "いします", "いただき", "お願いし",
    }

    loops = []
    clean_text = "".join([c for c in text if c.isalnum()])

    for n in n_range:
        ngrams = {}
        for i in range(len(clean_text) - n + 1):
            gram = clean_text[i:i+n]
            if gram in JAPANESE_COMMON_GRAMS:
                continue  # Skip legitimate Japanese grammatical patterns
            ngrams[gram] = ngrams.get(gram, 0) + 1
            if ngrams[gram] > threshold:
                loops.append(f"'{gram}' repeated {ngrams[gram]}x")
                break  # Found a loop for this N, move to next N
    return loops


def _check_hallucination_guardrails(transcript: str, audio_duration: float, conn_id: str, log_prefix: str = "") -> dict:
    """
    Check for potential hallucination indicators.
    Updated for V5: More aggressive detection of short segments and common noise patterns.
    """
    reasons = []
    severity = "none"

    transcript_stripped = transcript.strip()
    transcript_len = len(transcript_stripped)

    _slog(conn_id, f"[Guardrail] {log_prefix}Checking: transcript_len={transcript_len}, audio_duration={audio_duration:.1f}s")

    # Check 1: Short transcript for long audio (potential truncation)
    if audio_duration > 8 and transcript_len < 6:
        reasons.append(f"Short transcript ({transcript_len} chars) for long audio ({audio_duration:.1f}s)")
        severity = "high"

    # Check 2: Very short transcript for medium audio
    if 3 < audio_duration <= 8 and transcript_len < 3:
        reasons.append(f"Very short transcript ({transcript_len} chars) for medium audio ({audio_duration:.1f}s)")
        severity = "medium"

    # Check 3: Language collapse patterns
    english_hallucination_patterns = [
        "now, how does", "so this call", "just to ask that", "how many times have you",
        "i'm sorry", "good morning", "good afternoon", "hi there", "hello,", "thank you,", 
        "you're welcome", "how does someone", "would you like to", "can i help you",
        "bye bye", "see you", "all right", "okay then"
    ]
    transcript_lower = transcript_stripped.lower()
    detected_patterns = [p for p in english_hallucination_patterns if p in transcript_lower]
    if detected_patterns and audio_duration > 3:
        reasons.append(f"Language collapse pattern: '{detected_patterns[0]}'")
        severity = "high"

    # Check 4: Noise-induced Japanese insertions (only flag if transcript IS exactly the pattern, very short audio)
    japanese_noise_only_patterns = [
        "お茶をどうぞ", "ただいま",
    ]
    if audio_duration < 2.0 and transcript_stripped in japanese_noise_only_patterns:
        reasons.append(f"Noise insertion pattern: '{transcript_stripped}'")
        severity = "high"

    # Check 5: Looping patterns
    loops = _detect_ngram_loops(transcript_stripped)
    if loops:
        reasons.append(f"Looping detected: {', '.join(loops)}")
        severity = "high"

    # Check 6: Empty transcript for non-silent audio
    if transcript_len == 0 and audio_duration > 2:
        reasons.append("Empty transcript for non-silent audio")
        severity = "medium"

    is_suspicious = len(reasons) > 0
    if is_suspicious:
        _slog(conn_id, f"[Guardrail] {log_prefix}WARNING - {'; '.join(reasons)} [severity={severity}]")
    else:
        _slog(conn_id, f"[Guardrail] {log_prefix}PASSED")

    return {
        "is_suspicious": is_suspicious,
        "reasons": reasons,
        "severity": severity,
    }


def _exact_overlap_chars(left: str, right: str) -> int:
    max_len = min(len(left), len(right))
    for size in range(max_len, 0, -1):
        if left.endswith(right[:size]):
            return size
    return 0


def _chunks_time_overlap(prev_info: dict | None, current_info: dict | None) -> bool:
    if not prev_info or not current_info:
        return False
    prev_end = prev_info.get("end_sec")
    current_start = current_info.get("start_sec")
    if prev_end is None or current_start is None:
        return False
    return current_start < prev_end



def _group_consecutive(indices: list[int]) -> list[list[int]]:
    """Group a list of integers into sub-lists of consecutive values."""
    if not indices:
        return []
    groups = [[indices[0]]]
    for idx in indices[1:]:
        if idx == groups[-1][-1] + 1:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return groups


def _find_healthy_neighbor(group: list[int], total_chunks: int, 
                           collapsed: list[int]) -> int | None:
    """Find a nearby chunk that is not part of the collapsed list to use as a context anchor."""
    # Try neighbor BEFORE the group first (better context)
    before = group[0] - 1
    if before >= 0 and before not in collapsed:
        return before
    # Try neighbor AFTER the group
    after = group[-1] + 1
    if after < total_chunks and after not in collapsed:
        return after
    return None


def _truncate_repetitions(text: str, n_range=(3, 4, 5, 6, 7, 8), threshold=2) -> str:
    """
    Detect and truncate tail-end repetitions (hallucinations).
    Example: "A B C B C B C" -> "A B C"
    """
    if not text:
        return text
    
    clean_text = text.strip()
    # Character-based check for Japanese
    for n in n_range:
        for t in range(threshold + 1, 1, -1): # Try higher thresholds first
            if len(clean_text) < n * t:
                continue
            
            tail = clean_text[-(n * t):]
            gram = tail[-n:]
            if gram * t == tail:
                # Found a loop! Truncate all but one instance of the gram
                # But only if it's at the very end
                return clean_text[:-(n * (t-1))]
    
    return clean_text


def _merge_chunk_transcripts(transcripts: list, chunk_infos: list | None = None, overlap_sec: float = CHUNK_OVERLAP_SEC) -> str:
    """
    Merge transcripts from chunks, trimming exact text duplicated by overlapping sub-chunks.
    
    Args:
        transcripts: List of (transcript, duration) tuples
        chunk_infos: Optional chunk metadata containing start_sec/end_sec.
        overlap_sec: Kept for backward compatibility.
    
    Returns:
        Merged transcript string
    """
    if not transcripts:
        return ""
    
    if len(transcripts) == 1:
        return transcripts[0][0]
    
    merged = _truncate_repetitions(transcripts[0][0])
    for i in range(1, len(transcripts)):
        chunk_text = _truncate_repetitions(transcripts[i][0])
        if chunk_text:
            prev_info = chunk_infos[i - 1] if chunk_infos and i - 1 < len(chunk_infos) else None
            current_info = chunk_infos[i] if chunk_infos and i < len(chunk_infos) else None
            if _chunks_time_overlap(prev_info, current_info):
                overlap_chars = _exact_overlap_chars(merged, chunk_text)
                if overlap_chars:
                    chunk_text = chunk_text[overlap_chars:]
            merged += chunk_text  # No space needed for Japanese
    
    return merged.strip()


def load_voxtral_model(model_id: str, load_in_4bit: bool = False):
    global model, processor, model_id_global, vad_model, vad_utils
    model_id_global = model_id
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[startup] fingerprint: {_server_fingerprint()}", flush=True)
    print(f"[startup] Loading model: {model_id} on {device}...", flush=True)

    # Load Silero VAD with retry logic for network resilience
    print("[startup] Loading Silero VAD...", flush=True)
    max_retries = 3
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            vad_model, outputs = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True,
                force_reload=False  # Use cached model if available
            )
            vad_utils = outputs
            print("[startup] Silero VAD loaded successfully.", flush=True)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[startup] VAD load failed (attempt {attempt + 1}/{max_retries}): {e}", flush=True)
                print(f"[startup] Retrying in {retry_delay}s...", flush=True)
                import time
                time.sleep(retry_delay)
            else:
                print(f"[startup] VAD load failed after {max_retries} attempts.", flush=True)
                print("[startup] ERROR: Cannot load Silero VAD. Try:", flush=True)
                print("[startup]   1. Check network connectivity", flush=True)
                print("[startup]   2. Run this in Colab first: torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True, force_reload=True)", flush=True)
                print("[startup]   3. Download model manually and set TORCH_HOME cache", flush=True)
                raise

    quantization_config = None
    if load_in_4bit and device == "cuda":
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        print("[startup] Using 4-bit quantization (NF4 + double quant) for VRAM safety on T4.", flush=True)

    model = VoxtralRealtimeForConditionalGeneration.from_pretrained(
        model_id,
        device_map="auto",
        quantization_config=quantization_config,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        trust_remote_code=False,  # Official model, no need
    )
    processor = AutoProcessor.from_pretrained(model_id)
    print("[startup] Model loaded successfully.", flush=True)
    print(f"[startup]   dtype : {model.dtype}", flush=True)
    print(f"[startup]   device: {next(model.parameters()).device}", flush=True)


def _run_inference_sync(audio_bytes: bytes, session_config: dict, conn_id: str, on_delta=None) -> dict:
    """Blocking inference — runs in a thread pool to keep the event loop free."""
    t0 = time.time()
    _slog(conn_id, f"inference_started  audio_bytes={len(audio_bytes)}")

    # Convert raw int16 PCM bytes -> float32 numpy array at 16kHz
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
    original_duration = len(audio_np) / 16000.0

    # =========================================================================
    # PREPROCESSING
    # =========================================================================
    audio_np = _preprocess_audio(audio_np, conn_id, sample_rate=16000)

    # =========================================================================
    # PHA 1: VAD-BASED TRIMMING
    # =========================================================================
    trimmed_audio, vad_info = _trim_silence_with_vad(audio_np, sample_rate=16000)
    
    # Log VAD results
    if vad_info.get("vad_error"):
        _slog(conn_id, f"VAD_warning: {vad_info['vad_error']}")
    
    if not vad_info.get("speech_detected", True):
        # No speech detected - return empty transcript
        _slog(conn_id, f"VAD: No speech detected in {original_duration:.2f}s audio, skipping inference")
        return _inference_result("", vad_info)
    
    trimmed_duration = vad_info.get("trimmed_duration", original_duration)
    if trimmed_duration < original_duration * 0.95:  # Only log if we actually trimmed >5%
        _slog(conn_id, f"VAD: Trimmed {original_duration:.2f}s → {trimmed_duration:.2f}s (removed {100*(1-trimmed_duration/original_duration):.1f}% silence)")
    
    # Check if trimmed audio is too short
    if trimmed_duration < 0.1:  # Less than 100ms
        _slog(conn_id, f"VAD: Trimmed audio too short ({trimmed_duration:.3f}s), skipping inference")
        return _inference_result("", vad_info)

    # =========================================================================
    # PHA 2: VAD-AWARE CHUNKED INFERENCE 
    # =========================================================================
    def run_inference_with_config(audio_to_process, temp_override=None):
        """Helper to run inference with optional temperature override."""
        if temp_override is not None:
            # Create a copy of session_config with modified temperature
            retry_config = session_config.copy()
            retry_config["temperature"] = str(temp_override)
        else:
            retry_config = session_config
            
        # Run VAD on the audio to get exact speech timestamps and chunk it
        sample_rate = 16000
        audio_tensor = torch.from_numpy(audio_to_process).to(torch.float32)
        get_speech_timestamps = vad_utils[0]
        
        speech_timestamps = get_speech_timestamps(
            audio_tensor, 
            vad_model, 
            sampling_rate=sample_rate,
            threshold=VAD_THRESHOLD,
            min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
            min_silence_duration_ms=VAD_SEGMENT_SILENCE_MS, # Use larger silence gap for chunking
        )
        
        chunks = _create_vad_aware_chunks(
            audio_to_process, 
            speech_timestamps, 
            sample_rate=sample_rate,
            max_chunk_sec=CHUNK_LIMIT_SEC,
            padding_ms=VAD_CHUNK_PADDING_MS
        )
        
        if not chunks:
            # Fallback: Treat as one single chunk if VAD missed it but we reached here
            chunks = [{
                "audio_np": audio_to_process,
                "start_sec": 0.0,
                "end_sec": len(audio_to_process) / sample_rate,
                "segments_count": 0,
                "is_sub_chunk": False,
            }]
            
        _slog(conn_id, f"Inference: Processing {len(chunks)} chunks...")
        transcripts = []
        chunk_infos = []
        
        for i, chunk_info in enumerate(chunks):
            # Use on_delta only for the first chunk to maintain client UI consistency
            current_on_delta = on_delta if (i == 0 and len(chunks) == 1) else None
            
            chunk_transcript, chunk_elapsed = _run_inference_for_chunk(chunk_info['audio_np'], retry_config, conn_id, current_on_delta)
            
            duration = chunk_info['end_sec'] - chunk_info['start_sec']
            transcripts.append((chunk_transcript, duration))
            chunk_infos.append(chunk_info)
        
        # ===== Phase 2: Language Collapse Recovery =====
        lang_retries = []
        if ENABLE_LANG_COLLAPSE_RECOVERY:
            collapsed_indices = []
            for i, (text, dur) in enumerate(transcripts):
                detection = _detect_language_collapse(text)
                if detection["is_collapsed"]:
                    collapsed_indices.append(i)
                    _slog(conn_id, f"[LangCollapse] Chunk {i+1} ({dur:.1f}s): {detection['reason']}")
            
            if collapsed_indices:
                groups = _group_consecutive(collapsed_indices)
                
                # Use temperature for all recovery attempts
                temp_retry_config = retry_config.copy()
                temp_retry_config["temperature"] = str(RETRY_TEMPERATURE)
                
                for group in groups:
                    anchor_idx = _find_healthy_neighbor(group, len(chunks), collapsed_indices)
                    if anchor_idx is None:
                        _slog(conn_id, f"[LangCollapse] No healthy anchor for group {group}, skipping retry")
                        lang_retries.append({"group": group, "status": "no_anchor"})
                        continue
                    
                    # Build retry audio: context prefix (5s) + collapsed chunk(s)
                    context_samples = int(LANG_COLLAPSE_CONTEXT_SEC * 16000)
                    anchor_audio = chunks[anchor_idx]['audio_np']
                    
                    if anchor_idx < group[0]:
                        # Anchor is BEFORE collapsed group → take last N seconds of anchor
                        context = anchor_audio[-context_samples:] if len(anchor_audio) > context_samples else anchor_audio
                    else:
                        # Anchor is AFTER collapsed group → take first N seconds of anchor
                        context = anchor_audio[:context_samples] if len(anchor_audio) > context_samples else anchor_audio
                    
                    # Concatenate collapsed chunks
                    collapsed_audio = np.concatenate([chunks[i]['audio_np'] for i in group])
                    
                    # Build retry audio
                    if anchor_idx < group[0]:
                        retry_audio = np.concatenate([context, collapsed_audio])
                    else:
                        retry_audio = np.concatenate([collapsed_audio, context])
                    
                    # Run retry inference
                    _slog(conn_id, f"[LangCollapse] Retrying group {group} with anchor {anchor_idx+1} ({len(retry_audio)/16000:.1f}s audio)")
                    retry_transcript, retry_elapsed = _run_inference_for_chunk(retry_audio, temp_retry_config, conn_id)
                    retry_detection = _detect_language_collapse(retry_transcript)
                    
                    if not retry_detection["is_collapsed"]:
                        # Retry succeeded! Extract only the collapsed portion's transcript
                        anchor_text = transcripts[anchor_idx][0]
                        if anchor_idx < group[0]:
                            # Context was at the beginning → trim anchor's text from start
                            overlap = _exact_overlap_chars(anchor_text, retry_transcript)
                            corrected_text = retry_transcript[overlap:] if overlap else retry_transcript
                        else:
                            # Context was at the end → trim anchor's text from end
                            overlap = _exact_overlap_chars(retry_transcript, anchor_text)
                            corrected_text = retry_transcript[:len(retry_transcript)-overlap] if overlap else retry_transcript
                        
                        # Replace collapsed chunks' transcripts
                        for j, idx in enumerate(group):
                            if j == 0:
                                transcripts[idx] = (corrected_text, transcripts[idx][1])
                            else:
                                transcripts[idx] = ("", transcripts[idx][1])
                        
                        lang_retries.append({"group": group, "anchor": anchor_idx, "status": "fixed"})
                        _slog(conn_id, f"[LangCollapse] Group {group} fixed via anchor chunk {anchor_idx+1}")
                    else:
                        # If retry with anchor failed AND it's Chunk 0, try fallback trim
                        if 0 in group:
                            _slog(conn_id, f"[LangCollapse] Group {group} retry FAILED, trying fallback for Chunk 0 (trim 500ms)")
                            cutoff_samples = int(0.5 * 16000)
                            group_audio = np.concatenate([chunks[i]['audio_np'] for i in group])
                            
                            if len(group_audio) > cutoff_samples + int(0.5 * 16000): # Ensure at least 0.5s remains
                                fallback_audio = group_audio[cutoff_samples:]
                                fallback_transcript, _ = _run_inference_for_chunk(fallback_audio, temp_retry_config, conn_id)
                                fallback_detection = _detect_language_collapse(fallback_transcript)
                                
                                if not fallback_detection["is_collapsed"]:
                                    for j, idx in enumerate(group):
                                        if j == 0:
                                            transcripts[idx] = (fallback_transcript, transcripts[idx][1])
                                        else:
                                            transcripts[idx] = ("", transcripts[idx][1])
                                    lang_retries.append({"group": group, "anchor": anchor_idx, "status": "fixed_fallback_trim"})
                                    _slog(conn_id, f"[LangCollapse] Group {group} fixed via 500ms trim fallback")
                                else:
                                    lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed_fallback"})
                                    _slog(conn_id, f"[LangCollapse] Group {group} fallback FAILED, keeping original")
                            else:
                                lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed_too_short"})
                                _slog(conn_id, f"[LangCollapse] Group {group} audio too short for fallback")
                        else:
                            lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed"})
                            _slog(conn_id, f"[LangCollapse] Group {group} retry FAILED (ratio {retry_detection['ascii_ratio']}), keeping original")
        
        # Merge transcripts
        transcript = _merge_chunk_transcripts(transcripts, chunk_infos)
        return transcript, lang_retries

    # Run primary inference (Trial 1)
    t_inf_start = time.time()
    transcript, lang_collapse_retries = run_inference_with_config(trimmed_audio)
    
    # =========================================================================
    # PHA 3: HALLUCINATION GUARDRAILS & MULTI-TEMPERATURE RETRY
    # =========================================================================
    guardrail_result = _check_hallucination_guardrails(transcript, trimmed_duration, conn_id, "[Primary] ")
    
    best_transcript = transcript
    best_severity = guardrail_result["severity"]
    severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    
    # Multi-temperature retry (if suspicious)
    if guardrail_result["is_suspicious"] and severity_order[best_severity] >= severity_order["medium"] and ENABLE_RETRY_HALLUCINATION:
        retry_temps = [0.2, 0.5]
        for r_temp in retry_temps:
            _slog(conn_id, f"[Guardrail] Severity {best_severity} detected. Attempting retry with temperature={r_temp}...")
            retry_transcript, _ = run_inference_with_config(trimmed_audio, temp_override=r_temp)
            retry_guardrail = _check_hallucination_guardrails(retry_transcript, trimmed_duration, conn_id, f"[Retry T={r_temp}] ")
            
            # If retry has lower severity, adopt it
            if severity_order[retry_guardrail["severity"]] < severity_order[best_severity]:
                _slog(conn_id, f"[Guardrail] Retry T={r_temp} improved severity: {best_severity} -> {retry_guardrail['severity']}")
                best_transcript = retry_transcript
                best_severity = retry_guardrail["severity"]
                guardrail_result = retry_guardrail
                if best_severity == "none":
                    break
            else:
                _slog(conn_id, f"[Guardrail] Retry T={r_temp} did not improve result (severity={retry_guardrail['severity']})")

    transcript = best_transcript
    elapsed = time.time() - t_inf_start
    
    _slog(conn_id, f"inference_finished  elapsed={elapsed:.2f}s  transcript_len={len(transcript)}  hallucination_warning={guardrail_result['is_suspicious']}")
    vad_result = dict(vad_info)
    vad_result["hallucination_warning"] = guardrail_result["is_suspicious"]
    vad_result["hallucination_severity"] = best_severity
    return _inference_result(transcript, vad_result, lang_collapse_retries)


async def run_inference(audio_bytes: bytes, session_config: dict, conn_id: str, on_delta=None) -> dict:
    """Async wrapper that offloads blocking inference to a thread pool."""
    return await asyncio.to_thread(_run_inference_sync, audio_bytes, session_config, conn_id, on_delta)


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": model_id_global or "mistralai/Voxtral-Mini-4B-Realtime-2602",
                "object": "model",
                "created": 1700000000,
                "owned_by": "mistral",
            }
        ],
    }


@app.websocket("/v1/realtime")
async def realtime_endpoint(websocket: WebSocket):
    loop = asyncio.get_running_loop()
    conn_id = uuid.uuid4().hex[:8]
    await websocket.accept()
    _slog(conn_id, "websocket_accepted")

    audio_buffer = bytearray()
    session_config = {"temperature": 0.0, "transcription_delay_ms": 480}
    accumulated_bytes = 0

    # VAD state for this connection (Priority 1)
    speech_detected = False
    last_vad_pos = 0
    
    # Online VAD segment tracking
    speech_segments = []           # Collected speech timestamps
    segment_check_pos = 0          # Position in audio buffer for VAD check
    last_segment_active = False    # Is there an active speech segment currently open?

    try:
        while True:
            message_text = await websocket.receive_text()
            data = json.loads(message_text)
            msg_type = data.get("type")
            payload_keys = ",".join(sorted(data.keys()))
            path_value = data.get("path")
            audio_value = data.get("audio")
            audio_len = len(audio_value) if isinstance(audio_value, str) else 0
            _slog(
                conn_id,
                f"message_received  type={msg_type!r}  keys=[{payload_keys}]"
                f"  path={path_value!r}  audio_b64_len={audio_len}",
            )

            if msg_type == "session.update":
                session_config.update(data.get("session", {}))
                # Note: transcription_delay_ms is currently a no-op in this implementation
                # but kept for protocol compatibility.
                _slog(conn_id, f"session_update  config={session_config}")

            elif msg_type == "input_audio_buffer.append":
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    chunk_bytes = base64.b64decode(audio_b64)
                    audio_buffer.extend(chunk_bytes)
                    accumulated_bytes += len(chunk_bytes)

                    # Incremental VAD check
                    # Run if we have at least 1536 samples (3072 bytes) which is ~96ms
                    # Silero VAD works well on 30ms-100ms chunks.
                    if (len(audio_buffer) - segment_check_pos) >= 3072:
                        try:
                            # Note: To correctly get timestamps over a continuous stream, 
                            # we should ideally run VAD over the whole buffer up to this point.
                            # For efficiency and to keep it simple while fixing hallucination,
                            # we will do a fast check on the whole buffer so far, 
                            # or just depend on the commit phase for exact chunking.
                            # In this incremental phase, we just maintain the binary speech_detected flag.
                            if not speech_detected:
                                check_bytes = audio_buffer[last_vad_pos:]
                                audio_np = np.frombuffer(check_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                                audio_tensor = torch.from_numpy(audio_np).to(torch.float32)
                                get_speech_timestamps = vad_utils[0]
                                speech_timestamps = get_speech_timestamps(
                                    audio_tensor, 
                                    vad_model, 
                                    sampling_rate=16000,
                                    threshold=VAD_THRESHOLD,
                                    min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
                                    min_silence_duration_ms=VAD_SEGMENT_SILENCE_MS,
                                )
                                if speech_timestamps:
                                    speech_detected = True
                                    _slog(conn_id, f"incremental_VAD: speech_detected at {accumulated_bytes} bytes")
                                last_vad_pos = len(audio_buffer)
                                
                            segment_check_pos = len(audio_buffer)
                        except Exception as e:
                            _slog(conn_id, f"incremental_VAD_error: {e}")

            elif msg_type == "input_audio_buffer.from_path":
                file_path = data.get("path", "")
                if file_path and os.path.exists(file_path):
                    try:
                        _slog(conn_id, f"loading_from_path  path={file_path}")
                        # Load via librosa, resample to 16kHz
                        audio_np, _ = librosa.load(file_path, sr=16000)
                        # Convert to int16 PCM bytes as expected by the buffer/inference logic
                        chunk_bytes = (audio_np * 32767).astype(np.int16).tobytes()
                        audio_buffer.extend(chunk_bytes)
                        accumulated_bytes += len(chunk_bytes)
                        _slog(conn_id, f"loaded_bytes  count={len(chunk_bytes)}")

                        # Trigger speech detection check for the loaded file
                        if not speech_detected:
                            audio_np_vad = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                            audio_tensor = torch.from_numpy(audio_np_vad).to(torch.float32)
                            get_speech_timestamps = vad_utils[0]
                            speech_timestamps = get_speech_timestamps(
                                audio_tensor, 
                                vad_model, 
                                sampling_rate=16000,
                                threshold=VAD_THRESHOLD,
                                min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
                                min_silence_duration_ms=VAD_SEGMENT_SILENCE_MS,
                            )
                            if speech_timestamps:
                                speech_detected = True
                                _slog(conn_id, "file_VAD: speech_detected in loaded path")
                            last_vad_pos = len(audio_buffer)
                    except Exception as e:
                        _slog(conn_id, f"load_error  path={file_path} error={e}")
                        await _safe_send_text(
                            websocket,
                            json.dumps({"type": "error", "error": {"message": f"Failed to load file: {e}"}}),
                            conn_id
                        )
                else:
                    _slog(conn_id, f"path_not_found  path={file_path}")
                    await _safe_send_text(
                        websocket,
                        json.dumps({"type": "error", "error": {"message": f"File not found: {file_path}"}}),
                        conn_id
                    )

            elif msg_type == "input_audio_buffer.commit":
                buf_size = len(audio_buffer)
                _slog(conn_id, f"commit_received  buffer_bytes={buf_size}  total_appended={accumulated_bytes}")
                if buf_size > 0:
                    try:
                        # Final VAD check if speech hasn't been detected yet (Priority 1)
                        if not speech_detected:
                            _slog(conn_id, "VAD: no speech detected in increments, running final check on full buffer")
                            audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32767.0
                            audio_tensor = torch.from_numpy(audio_np).to(torch.float32)
                            get_speech_timestamps = vad_utils[0]
                            speech_timestamps = get_speech_timestamps(
                                audio_tensor, 
                                vad_model, 
                                sampling_rate=16000,
                                threshold=VAD_THRESHOLD,
                                min_speech_duration_ms=VAD_MIN_SPEECH_DURATION_MS,
                            )
                            if speech_timestamps:
                                speech_detected = True

                        if not speech_detected:
                            _slog(conn_id, "VAD: silence confirmed, skipping inference")
                            await _safe_send_text(
                                websocket,
                                json.dumps(
                                    {
                                        "type": "response.audio_transcript.done",
                                        "transcript": "",
                                        "vad_config": _vad_config_metadata(),
                                        "vad_result": {
                                            "speech_detected": False,
                                            "original_duration": len(audio_buffer) / 32000.0,
                                            "trimmed_duration": len(audio_buffer) / 32000.0,
                                        },
                                    }
                                ),
                                conn_id
                            )
                        else:
                            _slog(conn_id, "VAD: speech present, starting inference")
                            # Launch inference in background thread
                            delta_futures = []
                            def on_delta_callback(delta):
                                fut = asyncio.run_coroutine_threadsafe(
                                    _safe_send_text(
                                        websocket,
                                        json.dumps({"type": "response.audio_transcript.delta", "delta": delta}),
                                        conn_id
                                    ),
                                    loop
                                )
                                delta_futures.append(fut)

                            inference_task = asyncio.create_task(
                                run_inference(bytes(audio_buffer), session_config, conn_id, on_delta_callback)
                            )
                            # Send keepalive pings while inference is running
                            # so ngrok / reverse proxies don't drop the connection
                            keepalive_n = 0
                            while not inference_task.done():
                                await asyncio.sleep(5)
                                if not inference_task.done():
                                    keepalive_n += 1
                                    success = await _safe_send_text(
                                        websocket,
                                        json.dumps({"type": "session.keepalive"}),
                                        conn_id
                                    )
                                    if not success:
                                        _slog(conn_id, "keepalive_failed: connection lost, cancelling inference")
                                        inference_task.cancel()
                                        break
                                    _slog(conn_id, f"keepalive_sent  n={keepalive_n}")
                            
                            try:
                                inference_payload = await inference_task
                            except asyncio.CancelledError:
                                _slog(conn_id, "inference_cancelled")
                                # Cleanup delta futures if any
                                for f in delta_futures: f.cancel()
                                return # Socket is likely already closed

                            transcript = inference_payload.get("transcript", "")
                            
                            # Flush delta messages before sending done
                            if delta_futures:
                                # Filter out cancelled futures
                                active_futs = [asyncio.wrap_future(f) for f in delta_futures if not f.cancelled()]
                                if active_futs:
                                    await asyncio.gather(*active_futs, return_exceptions=True)
                            
                            await _safe_send_text(
                                websocket,
                                json.dumps(
                                    {
                                        "type": "response.audio_transcript.done",
                                        "transcript": transcript,
                                        "vad_config": inference_payload.get("vad_config"),
                                        "vad_result": inference_payload.get("vad_result"),
                                        "lang_collapse_retries": inference_payload.get("lang_collapse_retries"),
                                    }
                                ),
                                conn_id
                            )
                            _slog(conn_id, f"transcript_sent  len={len(transcript)}")
                    except Exception as e:
                        if isinstance(e, (WebSocketDisconnect, RuntimeError)):
                            _slog(conn_id, f"inference_stopped_by_disconnect: {e}")
                        else:
                            _slog(conn_id, f"inference_error  {type(e).__name__}: {e}")
                            import traceback; traceback.print_exc()
                            await _safe_send_text(
                                websocket,
                                json.dumps({"type": "error", "error": {"message": str(e)}}),
                                conn_id
                            )
                    finally:
                        audio_buffer = bytearray()
                        accumulated_bytes = 0
                        speech_detected = False
                        last_vad_pos = 0
                else:
                    _slog(conn_id, "commit_received  buffer_empty → sending empty transcript")
                    await _safe_send_text(
                        websocket,
                        json.dumps(
                            {
                                "type": "response.audio_transcript.done",
                                "transcript": "",
                                "vad_config": _vad_config_metadata(),
                                "vad_result": {
                                    "speech_detected": False,
                                    "original_duration": 0.0,
                                    "trimmed_duration": 0.0,
                                },
                            }
                        ),
                        conn_id
                    )

            else:
                _slog(conn_id, f"unknown_message_type  raw_type={msg_type!r}  payload={data}")

    except WebSocketDisconnect:
        _slog(conn_id, "websocket_disconnected")
    except Exception as e:
        _slog(conn_id, f"websocket_error  {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voxtral Transformers FastAPI Server")
    parser.add_argument(
        "--model",
        type=str,
        default="mistralai/Voxtral-Mini-4B-Realtime-2602",
        help="HuggingFace model ID",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument(
        "--load-in-4bit",
        action="store_true",
        help="Enable 4-bit quantization (recommended for T4 GPU)",
    )

    args = parser.parse_args()
    load_voxtral_model(args.model, args.load_in_4bit)
    uvicorn.run(app, host=args.host, port=args.port)
