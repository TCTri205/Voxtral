import os
import json
import base64
import asyncio
import uuid
import time
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from transformers import VoxtralRealtimeForConditionalGeneration, AutoProcessor, TextIteratorStreamer
from mistral_common.tokens.tokenizers.audio import Audio
import argparse
import librosa # Added for server-side file loading
import threading

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
VAD_PADDING_MS = 500  # Padding around speech segments to avoid cutting off audio (Japanese: ~12 chars/sec, 500ms = ~6 chars safety margin)

# Silero VAD configuration (optimized for Japanese telephone audio)
VAD_THRESHOLD = 0.5  # Speech probability threshold (0.0-1.0)
VAD_MIN_SPEECH_DURATION_MS = 250  # Minimum speech segment duration to be considered
VAD_MIN_SILENCE_DURATION_MS = 100  # Minimum silence gap to split segments

# Online VAD-Aware Chunking config
VAD_SEGMENT_SILENCE_MS = 800   # Silence gap to split speech regions for chunking
VAD_CHUNK_PADDING_MS = 200     # Padding when cutting speech segment into chunks

# Hallucination guardrails config (via environment variable)
ENABLE_RETRY_HALLUCINATION = os.getenv("VOXTRAL_RETRY_HALLUCINATION", "false").lower() == "true"
RETRY_TEMPERATURE = 0.5  # Temperature for retry attempts

# ---------------------------------------------------------------------------
# Server revision fingerprint — printed at startup for Colab verification
# ---------------------------------------------------------------------------
_SERVER_VERSION = "2026-05-07.1"  # bump this string on every push


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
        "_SERVER_VERSION": _SERVER_VERSION,
    }


def _inference_result(transcript: str, vad_result: dict | None = None) -> dict:
    return {
        "transcript": transcript,
        "vad_config": _vad_config_metadata(),
        "vad_result": vad_result or {},
    }


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
        audio_tensor = torch.from_numpy(audio_np)
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
                # We have to split it blindly if a continuous speech piece is > max_chunk_sec
                sub_pos = 0
                overlap_samples = int(CHUNK_OVERLAP_SEC * sample_rate)
                while sub_pos < len(chunk_audio):
                    sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
                    sub_audio = chunk_audio[sub_pos:sub_end]
                    
                    actual_start_sec = (start_idx + sub_pos) / sample_rate
                    actual_end_sec = (start_idx + sub_end) / sample_rate
                    
                    chunks.append({
                        "audio_np": sub_audio,
                        "start_sec": actual_start_sec,
                        "end_sec": actual_end_sec,
                        "segments_count": len(current_chunk_segments) if sub_pos == 0 else 0,
                        "is_sub_chunk": True,
                    })
                    sub_pos += max_chunk_samples - overlap_samples
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
        sub_pos = 0
        overlap_samples = int(CHUNK_OVERLAP_SEC * sample_rate)
        while sub_pos < len(chunk_audio):
            sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
            sub_audio = chunk_audio[sub_pos:sub_end]
            chunks.append({
                "audio_np": sub_audio,
                "start_sec": (start_idx + sub_pos) / sample_rate,
                "end_sec": (start_idx + sub_end) / sample_rate,
                "segments_count": len(current_chunk_segments) if sub_pos == 0 else 0,
                "is_sub_chunk": True,
            })
            sub_pos += max_chunk_samples - overlap_samples
    else:
        chunks.append({
            "audio_np": chunk_audio,
            "start_sec": start_idx / sample_rate,
            "end_sec": end_idx / sample_rate,
            "segments_count": len(current_chunk_segments),
            "is_sub_chunk": False,
        })
        
    return chunks


def _run_inference_for_chunk(audio_np: np.ndarray, session_config: dict, conn_id: str, on_delta=None) -> str:
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

    # Setup streamer
    streamer = TextIteratorStreamer(processor.tokenizer, skip_special_tokens=True, skip_prompt=True)

    generation_kwargs = dict(
        **inputs,
        max_new_tokens=512,
        do_sample=do_sample,
        temperature=temperature if do_sample else None,
        streamer=streamer,
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


def _check_hallucination_guardrails(transcript: str, audio_duration: float, conn_id: str, log_prefix: str = "") -> dict:
    """
    Check for potential hallucination indicators.
    LOG ONLY MODE: Does not reject output, just logs warnings for evaluation.

    Args:
        transcript: The transcribed text
        audio_duration: Duration of the audio in seconds
        conn_id: Connection ID for logging
        log_prefix: Prefix for log messages (e.g., "[Primary]", "[Retry]")

    Returns:
        dict with 'is_suspicious', 'reasons', 'severity'
    """
    reasons = []
    severity = "none"

    transcript_stripped = transcript.strip()
    transcript_len = len(transcript_stripped)

    _slog(conn_id, f"[Guardrail] {log_prefix}Checking: transcript_len={transcript_len}, audio_duration={audio_duration:.1f}s")

    # Check 1: Short transcript for long audio (potential truncation or language collapse)
    if audio_duration > 10 and transcript_len < 10:
        reasons.append(f"Short transcript ({transcript_len} chars) for long audio ({audio_duration:.1f}s)")
        severity = "medium"

    # Check 2: Very short transcript for medium audio
    if 5 < audio_duration <= 10 and transcript_len < 5:
        reasons.append(f"Very short transcript ({transcript_len} chars) for medium audio ({audio_duration:.1f}s)")
        severity = "low"

    # Check 3: Detect potential language collapse (English words in Japanese audio context)
    # Focus on FULL English sentences/phrases that are clear hallucinations
    # Exclude loanwords/code names that may appear in Japanese business calls
    english_hallucination_patterns = [
        # Full sentence patterns (definite hallucinations)
        "now, how does", "so this call", "just to ask that", "how many times have you",
        "i'm sorry", "good morning", "good afternoon",
        # Conversational English (unlikely in Japanese business calls)
        "hi there", "hello,", "thank you,", "you're welcome",
        # Question patterns
        "how does someone", "would you like to", "can i help you",
    ]
    transcript_lower = transcript_stripped.lower()
    detected_patterns = [p for p in english_hallucination_patterns if p in transcript_lower]
    if len(detected_patterns) >= 1 and audio_duration > 5:
        reasons.append(f"Language collapse: detected English hallucination '{detected_patterns[0]}'")
        severity = "high"

    # Check 4: Detect repetitive/looping patterns (character-level repetition)
    if transcript_len > 50:
        # Check for repeated character sequences (e.g., "はい、ありがとうございます。はい、ありがとうございます。")
        # Split by common Japanese punctuation
        segments = transcript_stripped.replace("。", "\n").replace("、", "\n").split("\n")
        if len(segments) > 3:
            # Check if segments are highly repetitive
            unique_segments = set(segments)
            repetition_ratio = len(unique_segments) / len(segments)
            if repetition_ratio < 0.3:  # Less than 30% unique segments
                reasons.append(f"Looping: only {len(unique_segments)} unique segments out of {len(segments)}")
                severity = "high"

    # Check 5: Empty transcript for non-silent audio (VAD may have failed)
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
    
    merged = transcripts[0][0]
    for i in range(1, len(transcripts)):
        chunk_text = transcripts[i][0]
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
        audio_tensor = torch.from_numpy(audio_to_process)
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
            _slog(conn_id, "VAD: No speech found in run_inference_with_config")
            return "", 0.0
            
        if len(chunks) == 1:
            # Single chunk - process normally
            _slog(conn_id, f"Processing single VAD chunk ({chunks[0]['start_sec']:.2f}s - {chunks[0]['end_sec']:.2f}s, {chunks[0]['segments_count']} segments)")
            return _run_inference_for_chunk(chunks[0]['audio_np'], retry_config, conn_id, on_delta)
        else:
            # Process each chunk
            _slog(conn_id, f"VAD Chunking: Audio split into {len(chunks)} speech-only chunks")
            transcripts = []
            chunk_infos = []
            
            for i, chunk_info in enumerate(chunks):
                _slog(conn_id, f"Processing chunk {i+1}/{len(chunks)} ({chunk_info['start_sec']:.1f}s-{chunk_info['end_sec']:.1f}s, {chunk_info['segments_count']} segs)")
                
                # Only pass on_delta to the first chunk to avoid confusing the client 
                # (since deltas would be sent out of order relative to original audio if there are long gaps)
                # For now, we disable on_delta for chunked processing to keep it simple
                chunk_transcript, chunk_elapsed = _run_inference_for_chunk(chunk_info['audio_np'], retry_config, conn_id, None)
                
                _slog(conn_id, f"Chunk {i+1} done in {chunk_elapsed:.2f}s, transcript_len={len(chunk_transcript)}")
                duration = chunk_info['end_sec'] - chunk_info['start_sec']
                transcripts.append((chunk_transcript, duration))
                chunk_infos.append(chunk_info)
            
            # Merge transcripts
            transcript = _merge_chunk_transcripts(transcripts, chunk_infos)
            elapsed = time.time() - t0
            _slog(conn_id, f"chunked_inference_finished  elapsed={elapsed:.2f}s  total_chunks={len(chunks)}  transcript_len={len(transcript)}")
            return transcript, elapsed

    # Run primary inference
    transcript, elapsed = run_inference_with_config(trimmed_audio)

    # =========================================================================
    # PHA 3: HALLUCINATION GUARDRAILS (LOG ONLY MODE)
    # =========================================================================
    guardrail_result = _check_hallucination_guardrails(transcript, trimmed_duration, conn_id, "[Primary] ")

    # Retry logic (if enabled and suspicious output detected)
    if guardrail_result["is_suspicious"] and ENABLE_RETRY_HALLUCINATION:
        _slog(conn_id, f"[Guardrail] Retrying inference with temperature={RETRY_TEMPERATURE}")
        retry_transcript, retry_elapsed = run_inference_with_config(trimmed_audio, temp_override=RETRY_TEMPERATURE)

        # Check if retry produced better result
        retry_guardrail = _check_hallucination_guardrails(retry_transcript, trimmed_duration, conn_id, "[Retry] ")

        if not retry_guardrail["is_suspicious"] or len(retry_transcript) > len(transcript):
            _slog(conn_id, f"[Guardrail] Retry improved result: {len(retry_transcript)} chars vs {len(transcript)} chars")
            transcript = retry_transcript
            elapsed = retry_elapsed
            guardrail_result = retry_guardrail
        else:
            _slog(conn_id, f"[Guardrail] Retry did not improve result, keeping original")

    # LOG ONLY: Do not reject output - return transcript for evaluation
    _slog(conn_id, f"inference_finished  elapsed={elapsed:.2f}s  transcript_len={len(transcript)}  hallucination_warning={guardrail_result['is_suspicious']}")
    vad_result = dict(vad_info)
    vad_result["hallucination_warning"] = guardrail_result["is_suspicious"]
    return _inference_result(transcript, vad_result)


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
                                audio_tensor = torch.from_numpy(audio_np)
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
                            audio_tensor = torch.from_numpy(audio_np_vad)
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
                        await websocket.send_text(
                            json.dumps({"type": "error", "error": {"message": f"Failed to load file: {e}"}})
                        )
                else:
                    _slog(conn_id, f"path_not_found  path={file_path}")
                    await websocket.send_text(
                        json.dumps({"type": "error", "error": {"message": f"File not found: {file_path}"}})
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
                            audio_tensor = torch.from_numpy(audio_np)
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
                            await websocket.send_text(
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
                                )
                            )
                        else:
                            _slog(conn_id, "VAD: speech present, starting inference")
                            # Launch inference in background thread
                            delta_futures = []
                            def on_delta_callback(delta):
                                fut = asyncio.run_coroutine_threadsafe(
                                    websocket.send_text(
                                        json.dumps({"type": "response.audio_transcript.delta", "delta": delta})
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
                                    await websocket.send_text(
                                        json.dumps({"type": "session.keepalive"})
                                    )
                                    _slog(conn_id, f"keepalive_sent  n={keepalive_n}")
                            inference_payload = inference_task.result()
                            transcript = inference_payload.get("transcript", "")
                            
                            # Flush delta messages before sending done
                            if delta_futures:
                                await asyncio.gather(*(asyncio.wrap_future(f) for f in delta_futures))
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "response.audio_transcript.done",
                                        "transcript": transcript,
                                        "vad_config": inference_payload.get("vad_config"),
                                        "vad_result": inference_payload.get("vad_result"),
                                    }
                                )
                            )
                            _slog(conn_id, f"transcript_sent  len={len(transcript)}")
                    except Exception as e:
                        _slog(conn_id, f"inference_error  {type(e).__name__}: {e}")
                        import traceback; traceback.print_exc()
                        await websocket.send_text(
                            json.dumps({"type": "error", "error": {"message": str(e)}})
                        )
                    finally:
                        audio_buffer = bytearray()
                        accumulated_bytes = 0
                        speech_detected = False
                        last_vad_pos = 0
                else:
                    _slog(conn_id, "commit_received  buffer_empty → sending empty transcript")
                    await websocket.send_text(
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
                        )
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
