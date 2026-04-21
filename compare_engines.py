import argparse
import json
import os
from pathlib import Path


def load_results(results_dir):
    results_file = Path(results_dir) / "results.json"
    if not results_file.exists():
        raise FileNotFoundError(f"results.json not found in {results_dir}")
    
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_llm_summary(results_dir):
    summary_file = Path(results_dir) / "llm_eval_summary.json"
    if not summary_file.exists():
        return None
    
    with open(summary_file, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_stats(results):
    success = [r for r in results if r.get("status") == "success"]
    if not success:
        return None
    
    avg_total_rtf = sum(r.get("total_rtf", 0) for r in success) / len(success)
    avg_inf_rtf = sum(r.get("inference_rtf", 0) for r in success) / len(success)
    avg_connect = sum(r.get("connect_time", 0) for r in success) / len(success)
    avg_stream = sum(r.get("stream_time", 0) for r in success) / len(success)
    avg_wait = sum(r.get("wait_after_commit", 0) for r in success) / len(success)
    
    cer_vals = []
    for r in success:
        cer = r.get("cer", "N/A")
        if isinstance(cer, str) and cer.endswith("%"):
            try:
                cer_vals.append(float(cer.strip("%")) / 100)
            except:
                pass
    
    avg_cer = sum(cer_vals) / len(cer_vals) if cer_vals else None
    
    return {
        "total_files": len(results),
        "success_count": len(success),
        "avg_total_rtf": avg_total_rtf,
        "avg_inference_rtf": avg_inf_rtf,
        "avg_connect_time": avg_connect,
        "avg_stream_time": avg_stream,
        "avg_wait_after_commit": avg_wait,
        "avg_cer": avg_cer
    }


def main():
    parser = argparse.ArgumentParser(description="Compare ASR Engine Results")
    parser.add_argument("--voxtral-run", type=str, required=True, help="Voxtral results directory")
    parser.add_argument("--javis-run", type=str, required=True, help="Javis results directory")
    parser.add_argument("--output", type=str, help="Output report file (markdown)")
    
    args = parser.parse_args()
    
    voxtral_results = load_results(args.voxtral_run)
    javis_results = load_results(args.javis_run)
    
    voxtral_stats = compute_stats(voxtral_results)
    javis_stats = compute_stats(javis_results)
    
    if not voxtral_stats or not javis_stats:
        print("Error: Could not compute stats for one or both runs")
        return
    
    voxtral_summary = load_llm_summary(args.voxtral_run)
    javis_summary = load_llm_summary(args.javis_run)
    
    report = []
    report.append("# ASR Engine Comparison Report\n")
    report.append(f"- **Voxtral**: `{args.voxtral_run}`")
    report.append(f"- **Javis**: `{args.javis_run}`")
    report.append("")
    
    report.append("## Summary Statistics\n")
    report.append("| Metric | Voxtral | Javis | Diff |")
    report.append("| :--- | :--- | :--- | :--- |")
    report.append(f"| Total Files | {voxtral_stats['total_files']} | {javis_stats['total_files']} | - |")
    report.append(f"| Success | {voxtral_stats['success_count']} | {javis_stats['success_count']} | - |")
    
    rtf_diff = voxtral_stats['avg_inference_rtf'] - javis_stats['avg_inference_rtf']
    report.append(f"| Avg Inference RTF | {voxtral_stats['avg_inference_rtf']:.3f} | {javis_stats['avg_inference_rtf']:.3f} | {rtf_diff:+.3f} |")
    
    total_rtf_diff = voxtral_stats['avg_total_rtf'] - javis_stats['avg_total_rtf']
    report.append(f"| Avg Total RTF | {voxtral_stats['avg_total_rtf']:.3f} | {javis_stats['avg_total_rtf']:.3f} | {total_rtf_diff:+.3f} |")
    
    report.append(f"| Avg Connect Time (s) | {voxtral_stats['avg_connect_time']:.3f} | {javis_stats['avg_connect_time']:.3f} | - |")
    report.append(f"| Avg Stream Time (s) | {voxtral_stats['avg_stream_time']:.2f} | {javis_stats['avg_stream_time']:.2f} | - |")
    report.append(f"| Avg Wait Time (s) | {voxtral_stats['avg_wait_after_commit']:.2f} | {javis_stats['avg_wait_after_commit']:.2f} | - |")
    
    if voxtral_stats['avg_cer'] is not None and javis_stats['avg_cer'] is not None:
        cer_diff = (voxtral_stats['avg_cer'] - javis_stats['avg_cer']) * 100
        report.append(f"| Avg CER | {voxtral_stats['avg_cer']*100:.2f}% | {javis_stats['avg_cer']*100:.2f}% | {cer_diff:+.2f}% |")
    
    report.append("")
    report.append("## Per-File Comparison\n")
    report.append("| File | Voxtral RTF | Javis RTF | RTF Diff |")
    report.append("| :--- | :--- | :--- | :--- |")
    
    voxtral_map = {r["file"]: r for r in voxtral_results}
    javis_map = {r["file"]: r for r in javis_results}
    
    all_files = set(voxtral_map.keys()) | set(javis_map.keys())
    
    for fname in sorted(all_files):
        v = voxtral_map.get(fname)
        j = javis_map.get(fname)
        
        if v and v.get("status") == "success":
            v_rtf = v.get("inference_rtf", 0)
        else:
            v_rtf = "N/A"
        
        if j and j.get("status") == "success":
            j_rtf = j.get("inference_rtf", 0)
        else:
            j_rtf = "N/A"
        
        if isinstance(v_rtf, (int, float)) and isinstance(j_rtf, (int, float)):
            rtf_diff_val = v_rtf - j_rtf
            rtf_str = f"{rtf_diff_val:+.3f}"
        else:
            rtf_str = "-"
        
        report.append(f"| {fname} | {v_rtf} | {j_rtf} | {rtf_str} |")
    
    if voxtral_summary and javis_summary:
        report.append("")
        report.append("## LLM Hallucination Evaluation\n")
        
        v_hrs = voxtral_summary.get("hallucination_rate", "N/A")
        j_hrs = javis_summary.get("hallucination_rate", "N/A")
        
        if v_hrs != "N/A" and j_hrs != "N/A":
            hrs_diff = v_hrs - j_hrs
            report.append(f"| Hallucination Rate | {v_hrs:.3f} | {j_hrs:.3f} | {hrs_diff:+.3f} |")
        
        v_err = voxtral_summary.get("error_distribution", {})
        j_err = javis_summary.get("error_distribution", {})
        
        if v_err or j_err:
            report.append("")
            report.append("### Error Type Distribution\n")
            report.append("| Error Type | Voxtral | Javis |")
            report.append("| :--- | :--- | :--- |")
            
            all_err_types = set(v_err.keys()) | set(j_err.keys())
            for err_type in sorted(all_err_types):
                v_count = v_err.get(err_type, 0)
                j_count = j_err.get(err_type, 0)
                report.append(f"| {err_type} | {v_count} | {j_count} |")
        
        v_sev = voxtral_summary.get("severity_distribution", {})
        j_sev = javis_summary.get("severity_distribution", {})
        
        if v_sev or j_sev:
            report.append("")
            report.append("### Severity Distribution\n")
            report.append("| Severity | Voxtral | Javis |")
            report.append("| :--- | :--- | :--- |")
            
            all_sev = set(v_sev.keys()) | set(j_sev.keys())
            for sev in sorted(all_sev):
                v_count = v_sev.get(sev, 0)
                j_count = j_sev.get(sev, 0)
                report.append(f"| {sev} | {v_count} | {j_count} |")
    
    final_report = "\n".join(report)
    print(final_report)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_report)
        print(f"\nReport saved to: {args.output}")
    
    json_output = {
        "voxtral_run": args.voxtral_run,
        "javis_run": args.javis_run,
        "voxtral_stats": voxtral_stats,
        "javis_stats": javis_stats,
        "voxtral_hrs": voxtral_summary.get("hallucination_rate") if voxtral_summary else None,
        "javis_hrs": javis_summary.get("hallucination_rate") if javis_summary else None
    }
    
    if args.output:
        json_output_file = Path(args.output).with_name("comparison_summary.json")
    else:
        json_output_file = Path("comparison_summary.json")
    
    with open(json_output_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)
    print(f"Summary JSON saved to: {json_output_file}")


if __name__ == "__main__":
    main()