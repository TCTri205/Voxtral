import argparse
import subprocess
import os
import json
import time
import sys
import glob
from pathlib import Path

# Fix Windows console encoding (cp1252 -> utf-8) so Unicode transcripts print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", errors="replace", buffering=1)

def main():
    parser = argparse.ArgumentParser(description="Voxtral Benchmark Runner - Automated Multi-run Execution")
    parser.add_argument("--runs", type=int, default=1, help="Number of times to repeat the ASR run")
    parser.add_argument("--eval-only", action="store_true", help="Skip ASR and only run evaluation/aggregation on existing results")
    parser.add_argument("--run-dirs", type=str, help="Glob pattern for result directories (required for --eval-only, e.g. 'results/18-04-2026_v*')")
    parser.add_argument("--date", type=str, help="Specifically target all versions of a date (e.g. '18-04-2026'). Shortcut for --run-dirs 'results/DATE_v*'")
    parser.add_argument("--start-v", type=int, help="Starting version number for range filtering (inclusive)")
    parser.add_argument("--end-v", type=int, help="Ending version number for range filtering (inclusive)")

    # Arguments to pass through to run_asr.py or llm_evaluator
    parser.add_argument("--audio", type=str, help="Path to a single audio file")
    parser.add_argument("--audio_dir", type=str, help="Directory containing audio files")
    parser.add_argument("--host", type=str, help="Server host")
    parser.add_argument("--port", type=str, help="Server port")
    parser.add_argument("--delay", type=str, help="Transcription delay (ms)")
    parser.add_argument("--chunk-interval", type=str, help="Pacing (0.1 for realtime, 0 for throughput)")
    parser.add_argument("--response-timeout", type=str, help="Wait for transcript after commit")
    parser.add_argument("--debug", action="store_true", help="Detailed logs")
    parser.add_argument("--debug-frames", action="store_true", help="Log every chunk")
    parser.add_argument("--llm-eval", action="store_true", help="Run LLM-based hallucination evaluation")
    parser.add_argument("--llm-model", type=str, help="LLM model to use")
    parser.add_argument("--ground-truth", type=str, default="ground_truth.json", help="Path to ground_truth.json")
    parser.add_argument("--timestamps-dir", type=str, help="Path to timestamps directory")
    parser.add_argument("--server-audio-dir", type=str, help="Directory on the server where audio files are located")
    parser.add_argument("--engine", type=str, default="voxtral", choices=["voxtral", "javis"], help="ASR engine to benchmark")
    parser.add_argument("--ws-url", type=str, help="WebSocket URL for Javis")
    parser.add_argument("--language", type=str, default="ja", help="Language code for Javis")
    parser.add_argument("--noise-suppression", action="store_true", help="Enable noise suppression for Javis")
    parser.add_argument("--denoiser", type=str, default="demucs", help="Denoiser type for Javis")
    
    args, unknown = parser.parse_known_args()
    
    # Defensive check for unknown arguments that look like flags
    if unknown:
        flag_args = [arg for arg in unknown if arg.startswith("--")]
        if flag_args:
            print("=" * 60)
            print(f" WARNING: Unknown arguments detected: {', '.join(flag_args)}")
            print(" These will be forwarded directly to the engine script.")
            print(" If this was unintentional, please check your command line.")
            print("=" * 60)

    # Pre-process shortcuts
    if args.date:
        if not args.run_dirs:
            root = "results_javis" if args.engine == "javis" else "results"
            args.run_dirs = f"{root}/{args.date}_v*"
        else:
            print(f" Warning: Both --date and --run-dirs provided. Using --run-dirs: {args.run_dirs}")

    print("=" * 60)
    engine_name = args.engine.upper()
    print(f" {engine_name} BENCHMARK RUNNER ".center(60, "="))
    if args.eval_only:
        print(f" MODE: EVALUATION ONLY")
        print(f" Source: {args.run_dirs or 'N/A'}")
    else:
        print(f" MODE: FULL RUN (ASR + AUTO-EVAL)")
        print(f" Target: {args.audio or args.audio_dir or 'N/A'}")
        print(f" Config: {args.runs} runs")
    print("=" * 60)
    
    run_results_dirs = []
    start_timestamp = time.strftime("%Y%m%d_%H%M%S")

    if not args.eval_only:
        if not Path("run_asr.py").exists():
            print(f"Error: run_asr.py not found in {os.getcwd()}")
            sys.exit(1)

        for i in range(args.runs):
            print(f"\n>>> RUN {i+1} STARTING (Engine: {args.engine}) <<<\n")
            
            if args.engine == "voxtral":
                script = "run_asr.py"
            else:
                script = "run_asr_javis.py"
            
            cmd = ["python", script]
            if args.audio: cmd += ["--audio", args.audio]
            if args.audio_dir: cmd += ["--audio_dir", args.audio_dir]
            
            if args.engine == "voxtral":
                if args.host: cmd += ["--host", args.host]
                if args.port: cmd += ["--port", args.port]
                if args.delay: cmd += ["--delay", args.delay]
                if args.server_audio_dir: cmd += ["--server-audio-dir", args.server_audio_dir]
            else:
                if args.ws_url: cmd += ["--ws-url", args.ws_url]
                if args.language: cmd += ["--language", args.language]
                if args.noise_suppression: cmd += ["--noise-suppression"]
                if args.denoiser: cmd += ["--denoiser", args.denoiser]
            
            if args.chunk_interval is not None: cmd += ["--chunk-interval", args.chunk_interval]
            if args.response_timeout: cmd += ["--response-timeout", args.response_timeout]
            if args.debug: cmd += ["--debug"]
            if args.debug_frames: cmd += ["--debug-frames"]
            if args.llm_eval: cmd += ["--llm-eval"]
            if args.llm_model: cmd += ["--llm-model", args.llm_model]
            if args.ground_truth: cmd += ["--ground-truth", args.ground_truth]
            if args.timestamps_dir: cmd += ["--timestamps-dir", args.timestamps_dir]
            
            cmd += unknown

            my_env = os.environ.copy()
            my_env["PYTHONUNBUFFERED"] = "1"
            my_env["PYTHONUTF8"] = "1"          # Python 3.7+ UTF-8 mode (handles Japanese correctly)
            my_env["PYTHONIOENCODING"] = "utf-8"  # Fallback for older Pythons
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=my_env)
            
            current_run_dir = None
            for line in process.stdout:
                try:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Fallback: replace unencodable chars so the run continues
                    sys.stdout.write(line.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                
                clean_line = line.strip()
                if clean_line.startswith("New batch run:") or clean_line.startswith("Resuming batch in:"):
                    current_run_dir = clean_line.split(":", 1)[1].strip()
            
            process.wait()
            
            if current_run_dir and os.path.isdir(current_run_dir):
                run_results_dirs.append(current_run_dir)
                print(f"\n>>> RUN {i+1} COMPLETE: {current_run_dir} <<<\n")
            else:
                print(f"\n!!! RUN {i+1} FAILED to yield result directory !!!\n")
    else:
        if not args.run_dirs:
            print("Error: --run-dirs or --date is required when using --eval-only")
            sys.exit(1)
        
        if args.date:
            print(f" Target Date: {args.date} -> Pattern: {args.run_dirs}")

        raw_dirs = glob.glob(args.run_dirs)
        # Filter for directories only
        initial_dirs = [d for d in raw_dirs if os.path.isdir(d)]
        
        # Range Filtering Logic
        if args.start_v is not None or args.end_v is not None:
            run_results_dirs = []
            import re
            for d in initial_dirs:
                # Expecting pattern ending in _vN or DATE_vN or similar
                match = re.search(r"_v(\d+)$", d.rstrip("/\\"))
                if match:
                    v_num = int(match.group(1))
                    if args.start_v is not None and v_num < args.start_v: continue
                    if args.end_v is not None and v_num > args.end_v: continue
                    run_results_dirs.append(d)
                else:
                    # If it doesn't match the pattern, only include if no range filtering is actually active
                    if args.start_v is None and args.end_v is None:
                        run_results_dirs.append(d)
            print(f"Filtered {len(run_results_dirs)} directories from {len(initial_dirs)} found by glob.")
        else:
            run_results_dirs = initial_dirs
            print(f"Found {len(run_results_dirs)} directories matching pattern.")

        if args.llm_eval:
            for r_dir in run_results_dirs:
                results_json = Path(r_dir) / "results.json"
                if not results_json.exists():
                    print(f"Skipping {r_dir}: results.json not found.")
                    continue
                
                print(f"\n--- Running LLM Eval for {r_dir} ---")
                eval_cmd = [
                    "python", "-m", "llm_evaluator.batch_runner",
                    "--results", str(results_json),
                    "--ground-truth", args.ground_truth,
                    "--timestamps-dir", args.timestamps_dir or "timestamps"
                ]
                if args.llm_model:
                    eval_cmd += ["--model", args.llm_model]
                
                subprocess.run(eval_cmd)

    # Aggregation Phase
    if len(run_results_dirs) > 0:
        print("\n" + "=" * 60)
        print(" FINAL AGGREGATION ".center(60, "="))
        aggregate_stats(run_results_dirs, start_timestamp, args.engine)
        print("=" * 60)
    else:
        print("\nNo valid runs to aggregate.")

def aggregate_stats(run_dirs, timestamp, engine):
    all_runs_metrics = []
    
    for run_dir in run_dirs:
        results_path = Path(run_dir) / "results.json"
        if not results_path.exists(): continue
            
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: continue
            
        success_results = [r for r in data if r.get("status") == "success"]
        if not success_results: continue
            
        avg_total_rtf = sum(r.get('total_rtf', 0) for r in success_results) / len(success_results)
        avg_inf_rtf = sum(r.get('inference_rtf', 0) for r in success_results) / len(success_results)
        
        total_cer = 0
        cer_count = 0
        for r in success_results:
            fname = r.get("file", "").lower()
            # Exclude silence/noise files from CER average
            if any(kw in fname for kw in ["silence", "noise", "stochastic"]):
                continue

            cer_str = r.get("cer", "N/A")
            if isinstance(cer_str, str) and cer_str.endswith("%"):
                try:
                    total_cer += float(cer_str.strip("%")) / 100
                    cer_count += 1
                except: pass
        
        avg_cer = total_cer / cer_count if cer_count > 0 else None
        
        all_runs_metrics.append({
            "dir": run_dir,
            "avg_total_rtf": avg_total_rtf,
            "avg_inf_rtf": avg_inf_rtf,
            "avg_cer": avg_cer
        })

    if not all_runs_metrics:
        print("No successful result data found across any runs.")
        return

    # Final Average
    count = len(all_runs_metrics)
    f_total_rtf = sum(m["avg_total_rtf"] for m in all_runs_metrics) / count
    f_inf_rtf = sum(m["avg_inf_rtf"] for m in all_runs_metrics) / count
    
    cers = [m["avg_cer"] for m in all_runs_metrics if m["avg_cer"] is not None]
    f_cer = (sum(cers) / len(cers)) if cers else None

    print(f"Total Runs Aggregated: {count}")
    print(f"Average Total RTF:     {f_total_rtf:.4f}")
    print(f"Average Inference RTF: {f_inf_rtf:.4f}")
    if f_cer is not None:
        print(f"Average CER:           {f_cer*100:.2f}%")

    # Save summary
    root = "benchmarks_javis" if engine == "javis" else "benchmarks"
    summary_dir = Path(root)
    summary_dir.mkdir(exist_ok=True)
    summary_path = summary_dir / f"benchmark_{timestamp}.json"
    
    summary_data = {
        "engine": engine,
        "timestamp_start": timestamp,
        "timestamp_end": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runs_passed": len(run_dirs),
        "runs_aggregated": count,
        "averages": {
            "total_rtf": f_total_rtf,
            "inference_rtf": f_inf_rtf,
            "cer_percentage": (f_cer*100) if f_cer is not None else None
        },
        "details": all_runs_metrics
    }
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=4)
    print(f"\nFinal summary written to: {summary_path}")

if __name__ == "__main__":
    main()
