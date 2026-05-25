import argparse
import asyncio
import base64
import json
import numpy as np
import librosa
import websockets
import time
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Fix Windows console encoding (cp1252 -> utf-8) so Unicode transcripts are handled correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1)

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Test convention reference (not enforced at runtime)
# ---------------------------------------------------------------------------
# smoke test          : very short file, chunk_interval=0
#                       → verifies server realtime path, not latency
# protocol/ngrok test : short file, chunk_interval=0.1
#                       → verifies end-to-end protocol through tunnel
# e2e latency test    : real file, chunk_interval=0.1
#                       → measures realistic latency (streaming takes ~file_duration before commit)
# throughput test     : real file, chunk_interval=0
#                       → measures max server throughput, not a realtime benchmark
#
# WARNING: with chunk_interval=0.1 a file of duration D will take ~D seconds
# just to stream before the server even begins inference.
# ---------------------------------------------------------------------------


def build_realtime_uri(host, port):
    raw_host = (host or "localhost").strip()
    parsed = urlparse(raw_host if "://" in raw_host else f"//{raw_host}")

    hostname = parsed.hostname or parsed.path or "localhost"
    hostname = hostname.strip("/")
    is_ngrok = ".ngrok" in hostname.lower()
    scheme_map = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}
    scheme = scheme_map.get(parsed.scheme, parsed.scheme) or ("wss" if is_ngrok else "ws")
    effective_port = parsed.port or port

    if is_ngrok and effective_port == 8000 and parsed.port is None:
        return f"{scheme}://{hostname}/v1/realtime"

    return f"{scheme}://{hostname}:{effective_port}/v1/realtime"


def _ts():
    """Return a short HH:MM:SS.mmm timestamp for diagnostic output."""
    t = time.time()
    ms = int((t % 1) * 1000)
    s = int(t)
    hh = (s // 3600) % 24
    mm = (s % 3600) // 60
    ss = s % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"


def log(msg, log_file=None, end="\n", flush=False):
    """Print to console and optionally append to a log file."""
    print(msg, end=end, flush=flush)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(str(msg) + end)
        except Exception as e:
            print(f"Error writing to log file: {e}")


async def transcription_client(
    audio_path,
    host="localhost",
    port=8000,
    delay=480,
    chunk_interval=0.1,
    response_timeout=30,
    debug=False,
    debug_frames=False,
    log_file=None,
    server_audio_path=None,  # New argument for direct access
    language="ja",  # Language code for transcription
    vad_commit=False,
    vad_silence_ms=800,
    vad_max_len_ms=10000,
    vad_min_len_ms=500,
    vad_mode=3,
):
    uri = build_realtime_uri(host, port)
    if debug:
        log(f" Connecting to: {uri}", log_file)

    try:
        # Load audio and get duration
        if server_audio_path:
            # We can't easily get duration from a server path without making the server report it,
            # but we can try to get it locally if the file exists here too (which it usually does in this repo).
            if os.path.exists(audio_path):
                audio_tmp, sr_tmp = librosa.load(audio_path, sr=16000)
                duration = librosa.get_duration(y=audio_tmp, sr=sr_tmp)
            else:
                duration = 0 # Fallback
        else:
            audio, sr = librosa.load(audio_path, sr=16000)
            duration = librosa.get_duration(y=audio, sr=sr)

        start_time = time.time()
        
        # 1. Connect Phase
        t_start_connect = time.time()
        async with websockets.connect(uri) as websocket:
            t_connected = time.time()
            connect_time = t_connected - t_start_connect

            # Send configuration
            config = {
                "type": "session.update",
                "session": {
                    "transcription_delay_ms": delay,
                    "modalities": ["text"],
                    "temperature": 0.0,
                    "language": language  # Language hint for ASR
                }
            }
            await websocket.send(json.dumps(config))

            # Multi-Commit states
            sent_commits = set()
            completed_commits = set()
            transcripts = {}
            raw_transcripts = {}
            chunk_telemetry_all = []
            commit_send_times = {}
            commit_wait_times = {}
            keepalive_peak_all = 0
            server_errors = []
            vad_config = None
            vad_result = None
            last_activity_time = time.time()

            async def receiver():
                nonlocal keepalive_peak_all, vad_config, vad_result, last_activity_time
                while True:
                    try:
                        message = await websocket.recv()
                        last_activity_time = time.time()
                        data = json.loads(message)
                        msg_type = data.get("type")
                        cid = data.get("commit_id") or 1

                        if msg_type == "response.audio_transcript.delta":
                            delta = data.get("delta", "")
                            if delta:
                                print(delta, end="", flush=True)
                                
                        elif msg_type == "response.audio_transcript.done":
                            transcript = data.get("transcript", "")
                            raw_transcript = data.get("raw_transcript", transcript)
                            transcripts[cid] = transcript
                            raw_transcripts[cid] = raw_transcript
                            
                            vad_config = data.get("vad_config")
                            vad_result = data.get("vad_result")
                            
                            if cid in commit_send_times:
                                wait_time = time.time() - commit_send_times[cid]
                                commit_wait_times[cid] = wait_time
                            
                            # Store telemetries
                            chunk_telemetry = data.get("chunk_telemetry", [])
                            chunk_telemetry_all.extend(chunk_telemetry)
                            
                            keepalive_peak = data.get("keepalive_peak", 0)
                            if keepalive_peak > keepalive_peak_all:
                                keepalive_peak_all = keepalive_peak
                                
                            completed_commits.add(cid)
                            if debug:
                                log(f"\n[Receiver] Commit {cid} done. Transcript: '{transcript}'", log_file)
                                
                        elif msg_type == "session.keepalive":
                            if debug:
                                log(f"\n[Receiver] Keepalive received for commit {cid}", log_file)
                                
                        elif msg_type == "error":
                            err_msg = data.get("error", {}).get("message", "Unknown error")
                            server_errors.append(err_msg)
                            log(f"\n[Server Error] commit {cid}: {err_msg}", log_file)
                            completed_commits.add(cid) # Count as completed so client doesn't hang
                            
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception as e:
                        log(f"\n[Receiver Exception]: {e}", log_file)
                        break

            # Start concurrent receiver task
            receiver_task = asyncio.create_task(receiver())

            # 2. Stream Phase (or Path Phase)
            t_start_stream = time.time()
            chunks_sent = 0
            bytes_sent = 0
            commit_id_counter = 0
            has_uncommitted_audio = False

            if server_audio_path:
                if debug:
                    log(f" Requesting server-side load: {server_audio_path}", log_file)
                await websocket.send(json.dumps({
                    "type": "input_audio_buffer.from_path",
                    "path": server_audio_path
                }))
                bytes_sent = -1 
                has_uncommitted_audio = True
            else:
                # Initialize WebRTC VAD if enabled
                vad = None
                is_speaking = False
                speech_duration_ms = 0
                silence_duration_ms = 0

                if vad_commit:
                    import webrtcvad
                    vad = webrtcvad.Vad(vad_mode)
                    if debug:
                        log(f" [VAD] Initialized WebRTC VAD with mode {vad_mode}", log_file)

                chunk_size = int(16000 * 0.1) # 100ms
                for i in range(0, len(audio), chunk_size):
                    chunk = audio[i:i + chunk_size]
                    chunk_int16 = (chunk * 32767).astype(np.int16)
                    audio_base64 = base64.b64encode(chunk_int16.tobytes()).decode('utf-8')

                    payload = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_base64
                    }
                    await websocket.send(json.dumps(payload))
                    chunks_sent += 1
                    bytes_sent += len(chunk_int16.tobytes())
                    has_uncommitted_audio = True

                    if debug_frames:
                        print(f"[DBG {_ts()}] chunk={chunks_sent} bytes={bytes_sent}")

                    # Run WebRTC VAD
                    if vad is not None:
                        frame_size = 640  # 20ms frame at 16kHz (320 samples * 2 bytes)
                        chunk_bytes = chunk_int16.tobytes()
                        frame_bytes_list = [chunk_bytes[offset:offset+frame_size] 
                                            for offset in range(0, len(chunk_bytes), frame_size)]
                        
                        for frame_data in frame_bytes_list:
                            if len(frame_data) == frame_size:
                                is_speech = vad.is_speech(frame_data, 16000)
                                if is_speech:
                                    speech_duration_ms += 20
                                    silence_duration_ms = 0
                                    if speech_duration_ms >= vad_min_len_ms and not is_speaking:
                                        is_speaking = True
                                        if debug:
                                            log(f"\n[VAD {_ts()}] Speech started", log_file)
                                else:
                                    silence_duration_ms += 20

                        # Check triggers
                        trigger_commit = False
                        if is_speaking:
                            if silence_duration_ms >= vad_silence_ms:
                                trigger_commit = True
                                if debug:
                                    log(f"\n[VAD {_ts()}] Pause detected ({silence_duration_ms}ms silence >= {vad_silence_ms}ms)", log_file)
                            elif speech_duration_ms >= vad_max_len_ms:
                                trigger_commit = True
                                if debug:
                                    log(f"\n[VAD {_ts()}] Max duration reached ({speech_duration_ms}ms >= {vad_max_len_ms}ms)", log_file)

                        if trigger_commit:
                            commit_id_counter += 1
                            await websocket.send(json.dumps({
                                "type": "input_audio_buffer.commit", 
                                "commit_id": commit_id_counter
                            }))
                            commit_send_times[commit_id_counter] = time.time()
                            sent_commits.add(commit_id_counter)
                            
                            # Reset VAD state for next segment
                            is_speaking = False
                            speech_duration_ms = 0
                            silence_duration_ms = 0
                            has_uncommitted_audio = False

                    if chunk_interval > 0:
                        # Precise pacing
                        target_time = t_start_stream + (chunks_sent * chunk_interval)
                        sleep_time = target_time - time.time()
                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)

            # Final Commit if anything remains
            if has_uncommitted_audio:
                commit_id_counter += 1
                await websocket.send(json.dumps({
                    "type": "input_audio_buffer.commit", 
                    "commit_id": commit_id_counter
                }))
                commit_send_times[commit_id_counter] = time.time()
                sent_commits.add(commit_id_counter)

            t_committed = time.time()
            stream_time = t_committed - t_start_stream

            # 4. Wait Phase (Wait for all commits to complete)
            t_start_wait = time.time()
            while len(completed_commits) < len(sent_commits):
                if server_errors:
                    return {
                        "status": "failed",
                        "error_type": "server_error",
                        "error_message": "; ".join(server_errors)
                    }
                if time.time() - last_activity_time > response_timeout:
                    wait_elapsed = time.time() - t_start_wait
                    log(f"\n[Timeout] {os.path.basename(audio_path)}: Timeout waiting for commits ({len(completed_commits)}/{len(sent_commits)} done) after {wait_elapsed:.2f}s (no server activity for {response_timeout}s)", log_file)
                    receiver_task.cancel()
                    return {
                        "status": "failed",
                        "error_type": "timeout",
                        "wait_after_commit": round(wait_elapsed, 2),
                        "keepalive_count": len(completed_commits)
                    }
                await asyncio.sleep(0.1)

            t_received = time.time()
            receiver_task.cancel()
            await asyncio.gather(receiver_task, return_exceptions=True)

            print() # Print empty line to finish output cleanly

            # Gather final transcripts
            all_completed_ids = sorted(list(completed_commits))
            # Put spaces between segments for non-Japanese languages, but Japanese doesn't need spaces.
            separator = "" if language == "ja" else " "
            final_transcript = separator.join([transcripts.get(cid, "") for cid in all_completed_ids]).strip()
            final_raw_transcript = separator.join([raw_transcripts.get(cid, "") for cid in all_completed_ids]).strip()

            avg_wait_after_commit = sum(commit_wait_times.values()) / len(commit_wait_times) if commit_wait_times else 0.0
            total_time = t_received - start_time
            
            return {
                "file": os.path.basename(audio_path),
                "status": "success",
                "transcript": final_transcript,
                "raw_transcript": final_raw_transcript,
                "duration": round(duration, 2),
                "connect_time": round(connect_time, 3),
                "stream_time": round(stream_time, 2),
                "wait_after_commit": round(avg_wait_after_commit, 3),
                "total_time": round(total_time, 2),
                "total_rtf": round(total_time / duration, 3) if duration > 0 else None,
                "inference_rtf": round(avg_wait_after_commit / duration, 3) if duration > 0 else None,
                "keepalive_count": len(commit_wait_times),
                "keepalive_peak": keepalive_peak_all,
                "chunks_sent": chunks_sent,
                "bytes_sent": bytes_sent,
                "delay_ms": delay,
                "vad_config": vad_config,
                "vad_result": vad_result,
                "lang_collapse_retries": None,
                "chunk_telemetry": chunk_telemetry_all
            }

    except Exception as e:
        log(f"\n[Client Error] {os.path.basename(audio_path)}: {e}", log_file)
        import traceback; traceback.print_exc()
        return {
            "status": "failed",
            "error_type": "client_error",
            "error_message": str(e)
        }


async def main():
    parser = argparse.ArgumentParser(description="Voxtral ASR Client - Advanced Batch Processing")
    parser.add_argument("--audio", type=str, help="Path to a single audio file")
    parser.add_argument("--audio_dir", type=str, help="Directory containing audio files")
    parser.add_argument("--host", type=str, default=os.getenv("VOXTRAL_HOST", "localhost"), help="Server host")
    parser.add_argument("--port", type=int, default=int(os.getenv("VOXTRAL_PORT", 8000)), help="Server port")
    parser.add_argument("--delay", type=int, default=int(os.getenv("VOXTRAL_DELAY", 480)), help="Transcription delay (ms)")
    parser.add_argument("--language", type=str, default=os.getenv("VOXTRAL_LANGUAGE", "ja"), help="Language code for transcription (default: ja)")
    parser.add_argument("--resume", type=str, help="Folder path to resume a previous batch run (e.g. results/17-04-2026_v1)")
    parser.add_argument("--chunk-interval", type=float, default=0.1, help="Pacing (0.1 for realtime, 0 for throughput)")
    parser.add_argument("--response-timeout", type=float, default=30, help="Wait for transcript after commit")
    parser.add_argument("--debug", action="store_true", help="Detailed logs")
    parser.add_argument("--debug-frames", action="store_true", help="Log every chunk")
    parser.add_argument("--llm-eval", action="store_true", help="Run LLM-based hallucination evaluation")
    parser.add_argument("--llm-model", type=str, default="llama-3.3-70b-versatile", help="LLM model to use")
    parser.add_argument("--ground-truth", type=str, default="ground_truth.json", help="Path to ground_truth.json")
    parser.add_argument("--timestamps-dir", type=str, default="timestamps", help="Path to timestamps directory")
    parser.add_argument("--server-audio-dir", type=str, help="Directory on the server where audio files are located")
    parser.add_argument("--vad-commit", action="store_true", help="Enable VAD-based commits (Japan Natural Speech Pause)")
    parser.add_argument("--vad-silence-ms", type=int, default=800, help="VAD silence duration in ms to trigger commit")
    parser.add_argument("--vad-max-len-ms", type=int, default=10000, help="Max utterance duration in ms to force commit")
    parser.add_argument("--vad-min-len-ms", type=int, default=500, help="Min utterance duration in ms to trigger VAD speech state")
    parser.add_argument("--vad-mode", type=int, default=3, help="WebRTC VAD aggressiveness mode (0-3)")

    args = parser.parse_args()

    # 1. Output Directory Logic
    if args.resume:
        output_dir = Path(args.resume)
        if not output_dir.exists():
            parser.error(f"Resume directory not found: {args.resume}")
    else:
        date_str = time.strftime("%d-%m-%Y")
        v = 1
        while True:
            output_dir = Path(f"results/{date_str}_v{v}")
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
                break
            v += 1

    results_file = output_dir / "results.json"
    log_file = output_dir / "log_debug.txt"

    if args.resume:
        log(f"Resuming batch in: {output_dir}", log_file)
    else:
        log(f"New batch run: {output_dir}", log_file)

    # 2. Load Existing Results (Resume)
    existing_results = []
    processed_files = set()
    if results_file.exists():
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
                processed_files = {r["file"] for r in existing_results if r.get("status") == "success"}
        except Exception as e:
            log(f"Warning: Could not read existing results: {e}", log_file)

    # 3. Identify Files to Process
    audio_files = []
    if args.audio:
        audio_files.append(args.audio)
    if args.audio_dir:
        dir_path = Path(args.audio_dir)
        extensions = ('.mp3', '.wav', '.flac', '.m4a')
        audio_files.extend([str(f) for f in dir_path.iterdir() if f.suffix.lower() in extensions])

    pending_files = [f for f in audio_files if os.path.basename(f) not in processed_files]
    
    if args.resume:
        log(f"Found {len(audio_files)} files total, {len(processed_files)} already done, {len(pending_files)} pending.", log_file)
    else:
        log(f"Found {len(pending_files)} files to process.", log_file)

    results = existing_results

    # 4. Processing Loop
    for i, audio_path in enumerate(pending_files):
        fname = os.path.basename(audio_path)
        log(f"[{i+1}/{len(pending_files)}] {fname} ... ", log_file, end="", flush=True)
        
        server_path = None
        if args.server_audio_dir:
            server_path = str(Path(args.server_audio_dir) / fname).replace("\\", "/")

        res = await transcription_client(
            audio_path,
            args.host,
            args.port,
            args.delay,
            chunk_interval=args.chunk_interval,
            response_timeout=args.response_timeout,
            debug=args.debug,
            debug_frames=args.debug_frames,
            log_file=log_file,
            server_audio_path=server_path,
            language=args.language,
            vad_commit=args.vad_commit,
            vad_silence_ms=args.vad_silence_ms,
            vad_max_len_ms=args.vad_max_len_ms,
            vad_min_len_ms=args.vad_min_len_ms,
            vad_mode=args.vad_mode,
        )
        
        # Incremental Save
        if not res.get("file"):
            res["file"] = fname
        
        results.append(res)
        
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        if res.get("status") == "success":
            total_rtf_str = f"{res['total_rtf']:.3f}" if res['total_rtf'] is not None else "N/A"
            inf_rtf_str = f"{res['inference_rtf']:.3f}" if res['inference_rtf'] is not None else "N/A"
            log(f"Done (Total RTF: {total_rtf_str}, Inference RTF: {inf_rtf_str})", log_file)
        else:
            err_details = res.get('error_type')
            if res.get('error_message'):
                err_details += f": {res['error_message']}"
            log(f"Failed ({err_details})", log_file)

    # 5. Final Summary
    success_results = [r for r in results if r.get("status") == "success"]
    if success_results:
        # Avoid division by zero and handle None RTFs (Priority 3)
        valid_total_rtfs = [r['total_rtf'] for r in success_results if r['total_rtf'] is not None]
        valid_inf_rtfs = [r['inference_rtf'] for r in success_results if r['inference_rtf'] is not None]
        
        avg_total_rtf = sum(valid_total_rtfs) / len(valid_total_rtfs) if valid_total_rtfs else 0
        avg_inf_rtf = sum(valid_inf_rtfs) / len(valid_inf_rtfs) if valid_inf_rtfs else 0
        
        log(f"\nBatch complete. results in {results_file}", log_file)
        log(f"Processed: {len(success_results)}/{len(results)} success", log_file)
        log(f"Avg Total RTF: {avg_total_rtf:.3f}" if valid_total_rtfs else "Avg Total RTF: N/A", log_file)
        log(f"Avg Inference RTF: {avg_inf_rtf:.3f}" if valid_inf_rtfs else "Avg Inference RTF: N/A", log_file)

    # 6. Auto-generate Report
    report_file = output_dir / "report.md"
    log(f"\nGenerating evaluation report: {report_file} ...", log_file)
    try:
        subprocess.run([
            "python", "evaluate_metrics.py", 
            str(results_file), 
            "--gt", args.ground_truth,
            "--output", str(report_file)
        ], check=True)
        log("Report generated successfully.", log_file)
    except Exception as e:
        log(f"Warning: Could not generate report: {e}", log_file)

    # 7. LLM Evaluation
    if args.llm_eval:
        log(f"\nRunning LLM Evaluation ...", log_file)
        try:
            # We use python -m to ensure the package is correctly resolved
            subprocess.run([
                "python", "-m", "llm_evaluator.batch_runner",
                "--results", str(results_file),
                "--ground-truth", args.ground_truth,
                "--timestamps-dir", args.timestamps_dir,
                "--model", args.llm_model
            ], check=True)
            log("LLM Evaluation completed successfully.", log_file)
        except Exception as e:
            log(f"Warning: LLM Evaluation failed: {e}", log_file)


if __name__ == "__main__":
    asyncio.run(main())
