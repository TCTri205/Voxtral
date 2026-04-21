import asyncio
import argparse
import os
import sys
from dotenv import load_dotenv
from .data_loader import load_evaluation_candidates
from .voxtral_utils import calculate_hrs
# Delayed import of LLMCaller to support CLI-level verification without dependencies
from .report_exporter import (
    apply_heuristics, 
    export_csv, 
    export_summary_json, 
    export_markdown_report
)

async def main():
    parser = argparse.ArgumentParser(description="Voxtral LLM Hallucination Evaluator")
    parser.add_argument("--results", type=str, required=True, help="Path to results.json")
    parser.add_argument("--ground-truth", type=str, default="ground_truth.json", help="Path to ground_truth.json")
    parser.add_argument("--timestamps-dir", type=str, default="timestamps", help="Path to timestamps directory")
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile", help="LLM model to use")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent LLM calls")
    
    args = parser.parse_args()
    
    # Load environment variables (OPENAI_API_KEY, etc.)
    load_dotenv()
    
    if not os.path.exists(args.results):
        print(f"Error: Results file not found at {args.results}")
        sys.exit(1)

    run_dir = os.path.dirname(args.results)
    
    print(f"--- Starting LLM Evaluation for {run_dir} ---")
    
    # 1. Load candidates
    candidates = load_evaluation_candidates(
        results_json_path=args.results,
        ground_truth_path=args.ground_truth,
        timestamps_dir=args.timestamps_dir
    )
    
    if not candidates:
        print("No successful ASR results found to evaluate.")
        sys.exit(0)
    
    # We need full result dicts to calculate HRS
    import json
    with open(args.results, "r", encoding="utf-8") as f:
        full_results = json.load(f)
    
    stats = {
        "with_gt_timestamped": sum(1 for c in candidates if c.gt_timestamped),
        "without_gt_timestamped": sum(1 for c in candidates if not c.gt_timestamped),
        "hrs": calculate_hrs(full_results)
    }
    
    print(f"Loaded {len(candidates)} candidates.")
    print(f"  - With timestamped GT: {stats['with_gt_timestamped']}")
    print(f"  - Without timestamped GT: {stats['without_gt_timestamped']}")
    
    # 2. Call LLM
    print(f"Calling LLM ({args.model}) with concurrency={args.concurrency}...")
    try:
        from .llm_caller import LLMCaller
        caller = LLMCaller()
        results = await caller.evaluate_batch(
            candidates, 
            model=args.model, 
            concurrency=args.concurrency
        )
    except Exception as e:
        print(f"Error during LLM evaluation: {e}")
        sys.exit(1)
    
    # 3. Apply Heuristics
    results = apply_heuristics(results)
    
    # 4. Export Reports
    details_csv = os.path.join(run_dir, "llm_eval_details.csv")
    summary_json = os.path.join(run_dir, "llm_eval_summary.json")
    report_md = os.path.join(run_dir, "llm_eval_report.md")
    
    print(f"Exporting reports to {run_dir}...")
    export_csv(results, details_csv)
    export_summary_json(results, run_dir, args.model, summary_json, stats)
    export_markdown_report(results, summary_json, report_md)
    
    print("--- LLM Evaluation Completed ---")
    print(f"Details: {details_csv}")
    print(f"Summary: {summary_json}")
    print(f"Report:  {report_md}")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
