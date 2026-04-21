import json
import argparse
import re
import os
from pathlib import Path
from llm_evaluator.voxtral_utils import (
    normalize_japanese, 
    calculate_hrs,
    calculate_rf,
    calculate_cer
)


def classify_quality(hrs, cer, rtf):
    if hrs == 0 and cer < 0.01 and rtf < 0.1: return "S (Excellent)"
    if hrs < 0.5 and cer < 0.03 and rtf < 0.2: return "A (Good)"
    if hrs < 2.0 and cer < 0.10 and rtf < 0.5: return "B (Fair)"
    return "F (Fail)"

def main():
    parser = argparse.ArgumentParser(description="Voxtral ASR Evaluation Tooling")
    parser.add_argument("results_json", type=str, help="Path to results.json")
    parser.add_argument("--gt", type=str, help="Path to ground_truth.json (optional)")
    parser.add_argument("--output", type=str, help="Path to save report (markdown)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_json):
        print(f"Error: {args.results_json} not found.")
        return

    with open(args.results_json, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    gt_data = {}
    if args.gt and os.path.exists(args.gt):
        with open(args.gt, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

    # Metrics Summary
    hrs = calculate_hrs(results)
    
    report = []
    report.append("# Voxtral ASR Quality & Hallucination Report\n")
    report.append(f"Source: `{args.results_json}`")
    report.append(f"HRS (Hallucination Rate on Silence): **{hrs:.3f} CPM**\n")
    
    report.append("## Detailed Results per File\n")
    report.append("| File | Status | RTF (Inf) | HRS/RF | CER | Grade |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    total_cer = 0
    gt_count = 0
    
    for res in results:
        fname = res["file"]
        status = res.get("status", "success")
        rtf_inf = res.get("inference_rtf", 0)
        text = res.get("transcript", "")
        
        # Calculate RF
        rf = calculate_rf(text)
        
        # Calculate CER if GT exists and ASR was successful
        cer = "N/A"
        grade = "N/A"
        
        if status != "success":
            grade = "ERROR"
        elif fname in gt_data:
            ref = normalize_japanese(gt_data[fname])
            hyp = normalize_japanese(text)
            
            if not hyp and ref:
                # Transcript is empty but reference is not - likely a system failure
                cer = "N/A (Empty)"
                grade = "F (Fail)"
            else:
                cer_val = calculate_cer(hyp, ref)
                cer = f"{cer_val*100:.2f}%"
                total_cer += cer_val
                gt_count += 1
                grade = classify_quality(hrs if "silence" in fname.lower() else 0, cer_val, rtf_inf)
        else:
            # Fallback grade based on RTF and RF
            grade = "A" if rtf_inf < 0.2 and rf == 0 else "B" if rtf_inf < 0.5 else "F"

        res["rf"] = rf
        res["cer"] = cer
        report.append(f"| `{fname}` | {status} | {rtf_inf:.3f} | {rf} | {cer} | {grade} |")

    # Update results JSON with new metrics
    with open(args.results_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"Updated results saved to: {args.results_json}")

    if gt_count > 0:
        avg_cer = (total_cer / gt_count) * 100
        report.append(f"\n**Average CER (Ground Truth): {avg_cer:.2f}%**")

    final_report = "\n".join(report)
    print(final_report)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\nReport saved to: {args.output}")

if __name__ == "__main__":
    main()
