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
from transformers import VoxtralRealtimeForConditionalGeneration, AutoProcessor
from mistral_common.tokens.tokenizers.audio import Audio
import argparse
import librosa # Added for server-side file loading

app = FastAPI()

# Global variables for model and processor
model = None
processor = None
model_id_global = None

# ---------------------------------------------------------------------------
# Server revision fingerprint — printed at startup for Colab verification
# ---------------------------------------------------------------------------
_SERVER_VERSION = "2026-04-18.1"  # bump this string on every push


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


def load_voxtral_model(model_id: str, load_in_4bit: bool = False):
    global model, processor, model_id_global
    model_id_global = model_id
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[startup] fingerprint: {_server_fingerprint()}", flush=True)
    print(f"[startup] Loading model: {model_id} on {device}...", flush=True)

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


def _run_inference_sync(audio_bytes: bytes, session_config: dict, conn_id: str) -> str:
    """Blocking inference — runs in a thread pool to keep the event loop free."""
    t0 = time.time()
    _slog(conn_id, f"inference_started  audio_bytes={len(audio_bytes)}")

    # Convert raw int16 PCM bytes -> float32 numpy array at 16kHz
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0

    # Build an Audio object the way the official example shows
    audio_obj = Audio(
        audio_array=audio_np,
        sampling_rate=16_000,
        format="wav",
    )
    # Resample to the rate the feature extractor expects (usually 16kHz, but future-proof)
    audio_obj.resample(processor.feature_extractor.sampling_rate)

    inputs = processor(audio_obj.audio_array, return_tensors="pt")
    inputs = inputs.to(model.device, dtype=model.dtype)

    temperature = float(session_config.get("temperature", 0.0))
    do_sample = temperature > 0.0

    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
        )

    # Skip the prompt tokens when decoding
    input_len = inputs["input_ids"].shape[1] if "input_ids" in inputs else 0
    transcript = processor.batch_decode(
        generated_ids[:, input_len:], skip_special_tokens=True
    )[0].strip()

    elapsed = time.time() - t0
    _slog(conn_id, f"inference_finished  elapsed={elapsed:.2f}s  transcript_len={len(transcript)}")
    return transcript


async def run_inference(audio_bytes: bytes, session_config: dict, conn_id: str) -> str:
    """Async wrapper that offloads blocking inference to a thread pool."""
    return await asyncio.to_thread(_run_inference_sync, audio_bytes, session_config, conn_id)


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
    conn_id = uuid.uuid4().hex[:8]
    await websocket.accept()
    _slog(conn_id, "websocket_accepted")

    audio_buffer = bytearray()
    session_config = {"temperature": 0.0, "transcription_delay_ms": 480}
    accumulated_bytes = 0

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
                _slog(conn_id, f"session_update  config={session_config}")

            elif msg_type == "input_audio_buffer.append":
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    chunk_bytes = base64.b64decode(audio_b64)
                    audio_buffer.extend(chunk_bytes)
                    accumulated_bytes += len(chunk_bytes)

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
                        # Launch inference in background thread
                        inference_task = asyncio.create_task(
                            run_inference(bytes(audio_buffer), session_config, conn_id)
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
                        transcript = inference_task.result()
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "response.audio_transcript.done",
                                    "transcript": transcript,
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
                else:
                    _slog(conn_id, "commit_received  buffer_empty → sending empty transcript")
                    await websocket.send_text(
                        json.dumps(
                            {"type": "response.audio_transcript.done", "transcript": ""}
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
