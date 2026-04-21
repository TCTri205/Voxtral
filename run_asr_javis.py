import argparse
import asyncio
import json
import numpy as np
import librosa
import websockets
import time
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import javis_auth

load_dotenv()


def _ts():
    t = time.time()
    ms = int((t % 1) * 1000)
    s = int(t)
    hh = (s // 3600) % 24
    mm = (s % 3600) // 60
    ss = s % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"


def log(msg, log_file=None, end="\n", flush=False):
    print(msg, end=end, flush=flush)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(str(msg) + end)
        except Exception as e:
            print(f"Error writing to log file: {e}")


def validate_env():
    has_session = os.getenv("JAVIS_SESSION_ID") and os.getenv("JAVIS_TOKEN")
    has_creds = os.getenv("JAVIS_EMAIL") and os.getenv("JAVIS_PASSWORD")

    if not has_session and not has_creds:
        raise ValueError(
            "Missing Javis authentication configuration. "
            "Please provide (JAVIS_SESSION_ID and JAVIS_TOKEN) or (JAVIS_EMAIL and JAVIS_PASSWORD) in .env"
        )


async def transcription_client(
    audio_path,
    ws_url=None,
    chunk_interval=0.1,
    response_timeout=30,
    debug=False,
    debug_frames=False,
    log_file=None,
    language="ja",
    noise_suppression=False,
    denoiser="demucs",
    verify_with_transcribe_api=False,
):
    uri = ws_url or os.getenv("JAVIS_WS_URL")
    if not uri:
        raise ValueError("JAVIS_WS_URL not provided")

    session_id, token = javis_auth.get_javis_credentials(debug=debug)

    if debug:
        log(f" Connecting to: {uri}", log_file)

    try:
        if os.path.exists(audio_path):
            audio, sr = librosa.load(audio_path, sr=16000)
            duration = librosa.get_duration(y=audio, sr=sr)
        else:
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        t_start_connect = time.time()
        # Disable ping heartbeats to avoid 1011 keepalive ping timeout with Javis server
        async with websockets.connect(uri, ping_interval=None) as websocket:
            t_connected = time.time()
            connect_time = t_connected - t_start_connect

            if debug:
                log(f"[DBG {_ts()}] Connected, waiting for config...", log_file)

            config_msg = await asyncio.wait_for(websocket.recv(), timeout=response_timeout)
            config_data = json.loads(config_msg)
            if config_data.get("type") != "config":
                raise Exception(f"Expected config message, got: {config_data.get('type')}")

            if debug:
                log(f"[DBG {_ts()}] Received config, sending start...", log_file)

            start_payload = {
                "event": "start",
                "sample_rate": 16000,
                "format": "pcm16",
                "language": language,
                "detect_speaker": False,
                "noise_suppression": noise_suppression,
                "denoiser": denoiser,
                "webrtc_denoise_enabled": False,
                "webrtc_enable_ns": True,
                "webrtc_agc_type": 1,
                "webrtc_aec_type": 0,
                "webrtc_enable_vad": False,
                "webrtc_frame_ms": 10,
                "webrtc_ns_level": 0,
                "verify_with_transcribe_api": verify_with_transcribe_api,
                "save_processed_audio": False,
                "save_recorded_audio": False,
                "session_id": session_id,
                "token": token
            }

            await websocket.send(json.dumps(start_payload))

            ready_msg = await asyncio.wait_for(websocket.recv(), timeout=response_timeout)
            ready_data = json.loads(ready_msg)
            if ready_data.get("type") != "ready":
                if ready_data.get("type") == "error":
                    raise Exception(f"Server error: {ready_data.get('message')}")
                raise Exception(f"Expected ready message, got: {ready_data.get('type')}")

            if debug:
                log(f"[DBG {_ts()}] Ready received, streaming audio...", log_file)

            async def sender():
                t_stream_start = time.time()
                chunk_size = int(16000 * 0.1)
                bytes_sent = 0
                
                for i in range(0, len(audio), chunk_size):
                    chunk = audio[i:i + chunk_size]
                    chunk_int16 = (chunk * 32767).astype(np.int16)
                    audio_bytes = chunk_int16.tobytes()

                    await websocket.send(audio_bytes)
                    bytes_sent += len(audio_bytes)

                    if debug_frames:
                        chunk_num = i // chunk_size + 1
                        print(f"[DBG {_ts()}] chunk={chunk_num} bytes={bytes_sent}")

                    # Only pace if interval is set
                    if chunk_interval > 0:
                        target_time = t_stream_start + ((i // chunk_size + 1) * chunk_interval)
                        sleep_time = target_time - time.time()
                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)
                
                if debug:
                    log(f"[DBG {_ts()}] Audio streamed ({bytes_sent} bytes), sending stop...", log_file)
                
                await websocket.send(json.dumps({"event": "stop"}))
                return bytes_sent, time.time() - t_stream_start

            async def receiver():
                transcript = ""
                last_partial_text = ""
                t_received = None
                
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=response_timeout)
                    except asyncio.TimeoutError:
                        log(f"\n[Timeout] {os.path.basename(audio_path)}: No message for {response_timeout}s", log_file)
                        raise

                    if isinstance(message, bytes):
                        continue

                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "partial":
                        if debug:
                            log(f"[DBG {_ts()}] partial JSON: {message}", log_file)
                        
                        # Data structure: 'lines' vs 'text'
                        lines = data.get("lines", [])
                        if lines:
                            current_partial = " ".join(l.get("text", "") for l in lines if l.get("text"))
                        else:
                            current_partial = data.get("text", "")
                        
                        if current_partial:
                            last_partial_text = current_partial
                            
                        if debug:
                            log(f"[DBG {_ts()}] partial text: {current_partial[:50]}...", log_file)
                        continue

                    if msg_type == "final":
                        if debug:
                            log(f"[DBG {_ts()}] final JSON: {message}", log_file)
                        
                        t_received = time.time()
                        transcript = data.get("text", "")
                        
                        # Fallback for nested text structure
                        if not transcript:
                            lines = data.get("lines", [])
                            if lines:
                                transcript = " ".join(l.get("text", "") for l in lines if l.get("text"))
                        
                        if not transcript and data.get("segments"):
                            transcript = " ".join(seg.get("text", "") for seg in data.get("segments", []))
                        
                        # Ultimate fallback: use last partial if final is still empty
                        if not transcript:
                            transcript = last_partial_text
                        
                        return transcript, t_received

                    if msg_type == "error":
                        err_msg = data.get("message", str(data))
                        log(f"\n[Server Error] {os.path.basename(audio_path)}: {err_msg}", log_file)
                        raise Exception(f"Server error: {err_msg}")

                    if msg_type == "recorded_audio":
                        continue

            # Run sender and receiver concurrently
            # receiver continues until it gets "final"
            tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
            try:
                # results will be ((bytes_sent, stream_time), (transcript, t_received))
                results = await asyncio.gather(*tasks)
                (bytes_sent, stream_time), (transcript, t_received) = results
            except websockets.exceptions.ConnectionClosed as e:
                log(f"\n[Connection Closed] {os.path.basename(audio_path)}: {e}", log_file)
                # If we have some transcript from partials, we might want to return it
                # but for simplicity, treat as failure if receiver didn't finish
                return {
                    "status": "failed",
                    "error_type": "websocket_closed",
                    "error_message": str(e)
                }
            except Exception as e:
                # Ensure pending tasks are cancelled if one fails
                for task in tasks:
                    if not task.done():
                        task.cancel()
                raise
            finally:
                # Cleanup tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()

            wait_after_commit = t_received - (t_start_connect + connect_time + stream_time)
            total_time = t_received - start_time

            return {
                "file": os.path.basename(audio_path),
                "status": "success",
                "transcript": transcript,
                "duration": round(duration, 2),
                "connect_time": round(connect_time, 3),
                "stream_time": round(stream_time, 2),
                "wait_after_commit": round(wait_after_commit, 3),
                "total_time": round(total_time, 2),
                "total_rtf": round(total_time / duration, 3) if duration > 0 else 0,
                "inference_rtf": round(wait_after_commit / duration, 3) if duration > 0 else 0,
                "bytes_sent": bytes_sent,
                "engine": "javis",
                "profile": "raw-baseline"
            }

    except Exception as e:
        log(f"\n[Client Error] {os.path.basename(audio_path)}: {e}", log_file)
        return {
            "status": "failed",
            "error_type": "client_error",
            "error_message": str(e)
        }


async def main():
    validate_env()

    parser = argparse.ArgumentParser(description="Javis ASR Client - Benchmark Runner")
    parser.add_argument("--audio", type=str, help="Path to a single audio file")
    parser.add_argument("--audio_dir", type=str, help="Directory containing audio files")
    parser.add_argument("--resume", type=str, help="Folder path to resume a previous batch run")
    parser.add_argument("--ws-url", type=str, default=os.getenv("JAVIS_WS_URL"), help="WebSocket URL for Javis")
    parser.add_argument("--chunk-interval", type=float, default=0.1, help="Pacing (0.1 for realtime, 0 for throughput)")
    parser.add_argument("--response-timeout", type=float, default=30, help="Wait for transcript after stop")
    parser.add_argument("--debug", action="store_true", help="Detailed logs")
    parser.add_argument("--debug-frames", action="store_true", help="Log every chunk")
    parser.add_argument("--llm-eval", action="store_true", help="Run LLM-based hallucination evaluation")
    parser.add_argument("--llm-model", type=str, default="llama-3.3-70b-versatile", help="LLM model to use")
    parser.add_argument("--ground-truth", type=str, default="ground_truth.json", help="Path to ground_truth.json")
    parser.add_argument("--timestamps-dir", type=str, default="timestamps", help="Path to timestamps directory")
    parser.add_argument("--language", type=str, default="ja", help="Language code (ja, vi, en, auto)")
    parser.add_argument("--noise-suppression", action="store_true", help="Enable backend noise suppression")
    parser.add_argument("--denoiser", type=str, default="demucs", help="Denoiser type: demucs, df, webrtc")
    parser.add_argument("--verify-with-transcribe-api", action="store_true", help="Enable sentence verification")
    parser.add_argument("--output_root", type=str, default="results_javis", help="Root directory for output results")

    args = parser.parse_args()

    if args.resume:
        output_dir = Path(args.resume)
        if not output_dir.exists():
            parser.error(f"Resume directory not found: {args.resume}")
    else:
        date_str = time.strftime("%d-%m-%Y")
        v = 1
        while True:
            output_dir = Path(f"{args.output_root}/{date_str}_v{v}")
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

    existing_results = []
    processed_files = set()
    if results_file.exists():
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
                processed_files = {r["file"] for r in existing_results if r.get("status") == "success"}
        except Exception as e:
            log(f"Warning: Could not read existing results: {e}", log_file)

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

    for i, audio_path in enumerate(pending_files):
        fname = os.path.basename(audio_path)
        log(f"[{i+1}/{len(pending_files)}] {fname} ... ", log_file, end="", flush=True)

        res = await transcription_client(
            audio_path,
            ws_url=args.ws_url,
            chunk_interval=args.chunk_interval,
            response_timeout=args.response_timeout,
            debug=args.debug,
            debug_frames=args.debug_frames,
            log_file=log_file,
            language=args.language,
            noise_suppression=args.noise_suppression,
            denoiser=args.denoiser,
            verify_with_transcribe_api=args.verify_with_transcribe_api,
        )

        if not res.get("file"):
            res["file"] = fname

        results.append(res)

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

        if res.get("status") == "success":
            log(f"Done (Total RTF: {res['total_rtf']}, Inference RTF: {res['inference_rtf']})", log_file)
        else:
            err_details = res.get('error_type')
            if res.get('error_message'):
                err_details += f": {res['error_message']}"
            log(f"Failed ({err_details})", log_file)

    success_results = [r for r in results if r.get("status") == "success"]
    if success_results:
        avg_total_rtf = sum(r['total_rtf'] for r in success_results) / len(success_results)
        avg_inf_rtf = sum(r['inference_rtf'] for r in success_results) / len(success_results)
        log(f"\nBatch complete. results in {results_file}", log_file)
        log(f"Processed: {len(success_results)}/{len(results)} success", log_file)
        log(f"Avg Total RTF: {avg_total_rtf:.3f}", log_file)
        log(f"Avg Inference RTF: {avg_inf_rtf:.3f}", log_file)

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

    if args.llm_eval:
        log(f"\nRunning LLM Evaluation ...", log_file)
        try:
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
