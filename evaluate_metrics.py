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
    report.append("| File | Status | RTF (Inf) | HRS/RF | Raw CER | Adjusted CER | Grade |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    total_cer = 0
    cer_file_count = 0
    cer_total_files_with_gt = 0
    cer_excluded_files = []
    cer_silence_files = []
    empty_on_speech_count = 0
    deletion_count = 0
    
    # New standardized metrics lists
    cer_all_list = []
    cer_speech_only_list = []
    raw_cer_all_list = []
    raw_cer_speech_only_list = []
    
    for res in results:
        fname = res["file"]
        status = res.get("status", "success")
        rtf_inf = res.get("inference_rtf", 0)
        text = res.get("transcript", "")
        raw_text = res.get("raw_transcript", text)
        
        # Calculate RF
        rf = calculate_rf(text)
        
        # Calculate CER if GT exists and ASR was successful
        cer = "N/A"
        cer_speech_only = "N/A"
        cer_all_files = "N/A"
        raw_cer_str = "N/A"
        raw_cer_speech_only = "N/A"
        raw_cer_all_files = "N/A"
        grade = "N/A"
        
        is_silence = any(kw in fname.lower() for kw in ["silence", "noise", "stochastic"])
        
        if status != "success":
            grade = "ERROR"
        elif fname in gt_data:
            cer_total_files_with_gt += 1
            ref = normalize_japanese(gt_data[fname])
            hyp = normalize_japanese(text)
            raw_hyp = normalize_japanese(raw_text)
            
            cer_val = calculate_cer(hyp, ref)
            raw_cer_val = calculate_cer(raw_hyp, ref)
            
            # Add to standardized lists
            cer_all_list.append(cer_val)
            raw_cer_all_list.append(raw_cer_val)
            
            cer_all_files = f"{cer_val*100:.2f}%"
            raw_cer_all_files = f"{raw_cer_val*100:.2f}%"
            
            if not is_silence:
                cer_speech_only_list.append(cer_val)
                raw_cer_speech_only_list.append(raw_cer_val)
                cer_speech_only = f"{cer_val*100:.2f}%"
                raw_cer_speech_only = f"{raw_cer_val*100:.2f}%"
            else:
                cer_speech_only = "N/A (Silence/Noise)"
                raw_cer_speech_only = "N/A (Silence/Noise)"
            
            is_empty_on_speech = (not hyp and ref)
            if is_empty_on_speech:
                cer = f"{cer_val*100:.2f}% (Empty)"
                raw_cer_str = f"{raw_cer_val*100:.2f}% (Empty)"
                grade = "F (Fail)"
                cer_excluded_files.append(fname)
                empty_on_speech_count += 1
                deletion_count += 1
            else:
                cer = f"{cer_val*100:.2f}%"
                raw_cer_str = f"{raw_cer_val*100:.2f}%"
                if is_silence:
                    cer_silence_files.append(fname)
                else:
                    total_cer += cer_val
                    cer_file_count += 1
                grade = classify_quality(hrs if is_silence else 0, cer_val, rtf_inf)
        else:
            # Fallback grade based on RTF and RF
            grade = "A" if rtf_inf < 0.2 and rf == 0 else "B" if rtf_inf < 0.5 else "F"

        res["rf"] = rf
        res["cer"] = cer
        res["cer_speech_only"] = cer_speech_only
        res["cer_all_files"] = cer_all_files
        res["raw_cer"] = raw_cer_str
        res["raw_cer_speech_only"] = raw_cer_speech_only
        res["raw_cer_all_files"] = raw_cer_all_files
        
        report.append(f"| `{fname}` | {status} | {rtf_inf:.3f} | {rf} | {raw_cer_str} | {cer} | {grade} |")

    # Update results JSON with new metrics
    with open(args.results_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"Updated results saved to: {args.results_json}")

    report.append("\n## CER Accounting (Legacy)")
    report.append(f"- CER files included: **{cer_file_count}/{cer_total_files_with_gt}**")
    report.append(f"- CER excluded files: **{len(cer_excluded_files) + len(cer_silence_files)}**")
    report.append(f"  - Empty-on-speech (Fail): {len(cer_excluded_files)}")
    report.append(f"  - Silence/Noise (Intentional): {len(cer_silence_files)}")
    report.append(f"- Empty-on-speech count: **{empty_on_speech_count}**")
    report.append(f"- Deletion count: **{deletion_count}**")
    
    all_excluded = cer_excluded_files + cer_silence_files
    if all_excluded:
        report.append("- Excluded from CER average: " + ", ".join(f"`{name}`" for name in all_excluded))

    if cer_file_count > 0:
        avg_cer = (total_cer / cer_file_count) * 100
        excluded_total = len(cer_excluded_files) + len(cer_silence_files)
        report.append(f"\n**Average CER (Ground Truth - Legacy): {avg_cer:.2f}% ({cer_file_count}/{cer_total_files_with_gt} files; {excluded_total} excluded)**")

    # New Unified Standardized Metrics Section
    avg_cer_all = (sum(cer_all_list) / len(cer_all_list)) * 100 if cer_all_list else 0.0
    avg_cer_speech = (sum(cer_speech_only_list) / len(cer_speech_only_list)) * 100 if cer_speech_only_list else 0.0
    avg_raw_cer_all = (sum(raw_cer_all_list) / len(raw_cer_all_list)) * 100 if raw_cer_all_list else 0.0
    avg_raw_cer_speech = (sum(raw_cer_speech_only_list) / len(raw_cer_speech_only_list)) * 100 if raw_cer_speech_only_list else 0.0
    
    report.append("\n## Standardized Metrics Summary")
    report.append(f"- **Average Raw CER (All Files - Silence/Noise Included)**: **{avg_raw_cer_all:.2f}%** ({len(raw_cer_all_list)} files)")
    report.append(f"- **Average Adjusted CER (All Files - Silence/Noise Included)**: **{avg_cer_all:.2f}%** ({len(cer_all_list)} files)")
    report.append(f"- **Average Raw CER (Speech Only - Silence/Noise Excluded)**: **{avg_raw_cer_speech:.2f}%** ({len(raw_cer_speech_only_list)} files)")
    report.append(f"- **Average Adjusted CER (Speech Only - Silence/Noise Excluded)**: **{avg_cer_speech:.2f}%** ({len(cer_speech_only_list)} files)")

    final_report = "\n".join(report)
    print(final_report)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\nReport saved to: {args.output}")

if __name__ == "__main__":
    main()
