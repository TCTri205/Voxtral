import csv
import json
import os
from typing import List, Dict, Any
from .schema import EvaluationCandidate, EvaluationResult

def parse_cer(cer_str: str | None) -> float | None:
    """Parses CER string like '65.49%' or '100.00% (Empty)' to float."""
    if not cer_str or cer_str == "N/A" or cer_str.startswith("N/A"):
        return None
    try:
        clean_str = cer_str.replace("%", "").replace("(Empty)", "").strip()
        val = float(clean_str)
        return val / 100.0
    except ValueError:
        return None

def _has_empty_ground_truth(candidate: EvaluationCandidate | None) -> bool:
    if candidate is None:
        return False

    gt_values = [candidate.gt_plain, candidate.gt_timestamped]
    has_explicit_empty = any(gt is not None and gt.strip() == "" for gt in gt_values)
    has_non_empty = any(gt is not None and gt.strip() != "" for gt in gt_values)
    return has_explicit_empty and not has_non_empty


def apply_heuristics(
    results: List[EvaluationResult],
    candidates: List[EvaluationCandidate] | None = None,
) -> List[EvaluationResult]:
    """Applies heuristic overrides to evaluation results."""
    candidate_by_filename = {c.filename: c for c in candidates or []}

    for res in results:
        candidate = candidate_by_filename.get(res.filename)
        hyp = candidate.hyp_transcript if candidate is not None else res.evidence_hyp_text
        if (hyp or "").strip() == "" and _has_empty_ground_truth(candidate):
            res.review_status = "auto_accept"
            res.primary_error = "none"
            res.severity = "none"
            res.has_hallucination = False
            res.reasoning = "Empty transcript matches explicit empty ground truth."
            continue

        cer = parse_cer(res.existing_cer)
        if cer is not None and cer > 0.5:
            if not res.has_hallucination:
                res.review_status = "manual_review"
                res.reasoning += " (High CER heuristic override)"
    return results


def export_csv(results: List[EvaluationResult], output_path: str):
    """Exports results to CSV."""
    if not results:
        return
    
    fieldnames = [
        "filename", "has_hallucination", "primary_error", "severity", 
        "confidence", "review_status", "existing_cer", "existing_rf", 
        "existing_inference_rtf", "reasoning", "evidence_hyp_text", "evidence_gt_context"
    ]
    
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res.model_dump())

def export_summary_json(results: List[EvaluationResult], run_dir: str, model_used: str, output_path: str, candidate_stats: Dict[str, Any]):
    """Exports a summary JSON with aggregated metrics."""
    total = len(results)
    hallucinated = sum(1 for r in results if r.has_hallucination)
    manual_review = sum(1 for r in results if r.review_status == "manual_review")
    empty_on_speech_count = sum(1 for r in results if r.existing_cer and "Empty" in r.existing_cer)
    
    error_dist = {}
    severity_dist = {}
    
    total_cer = 0.0
    cer_count = 0
    total_rtf = 0.0
    rtf_count = 0
    
    # New standardized metrics
    cer_all_list = []
    cer_speech_only_list = []
    hallucinated_all_count = 0
    hallucinated_speech_only_count = 0
    total_speech_only_count = 0
    
    for r in results:
        error_dist[r.primary_error] = error_dist.get(r.primary_error, 0) + 1
        severity_dist[r.severity] = severity_dist.get(r.severity, 0) + 1
        
        is_silence = any(kw in r.filename.lower() for kw in ["silence", "noise", "stochastic"])
        
        cer = parse_cer(r.existing_cer)
        if cer is not None:
            total_cer += cer
            cer_count += 1
            
            cer_all_list.append(cer)
            if not is_silence:
                cer_speech_only_list.append(cer)
                
        if r.has_hallucination:
            hallucinated_all_count += 1
            if not is_silence:
                hallucinated_speech_only_count += 1
                
        if not is_silence:
            total_speech_only_count += 1
            
        if r.existing_inference_rtf is not None:
            total_rtf += r.existing_inference_rtf
            rtf_count += 1

    avg_cer_all_files = (sum(cer_all_list) / len(cer_all_list)) if cer_all_list else 0.0
    avg_cer_speech_only = (sum(cer_speech_only_list) / len(cer_speech_only_list)) if cer_speech_only_list else 0.0
    hallucination_rate_all_files = hallucinated_all_count / total if total > 0 else 0.0
    hallucination_rate_speech_only = hallucinated_speech_only_count / total_speech_only_count if total_speech_only_count > 0 else 0.0

    cer_total_files = candidate_stats.get("cer_total_files", candidate_stats.get("with_gt_plain", total))
    cer_excluded_files = candidate_stats.get("cer_excluded_files", empty_on_speech_count)

    summary = {
        "run_dir": run_dir,
        "model_used": model_used,
        "total_files": total,
        "evaluated_files": total,
        "total_speech_only_files": total_speech_only_count,
        "with_gt_timestamped": candidate_stats.get("with_gt_timestamped", 0),
        "without_gt_timestamped": candidate_stats.get("without_gt_timestamped", 0),
        "cer_file_count": cer_count,
        "cer_total_files": cer_total_files,
        "cer_excluded_files": cer_excluded_files,
        "empty_on_speech_count": empty_on_speech_count,
        "deletion_count": empty_on_speech_count,
        "hallucination_rate_all_files": round(hallucination_rate_all_files, 4),
        "hallucination_rate_speech_only": round(hallucination_rate_speech_only, 4),
        "hallucination_rate": round(hallucinated / total, 4) if total > 0 else 0, # Legacy
        "manual_review_rate": round(manual_review / total, 4) if total > 0 else 0,
        "error_distribution": error_dist,
        "severity_distribution": severity_dist,
        "existing_metrics": {
            "avg_cer_all_files": f"{avg_cer_all_files*100:.2f}%" if cer_all_list else "N/A",
            "avg_cer_speech_only": f"{avg_cer_speech_only*100:.2f}%" if cer_speech_only_list else "N/A",
            "avg_cer": f"{(total_cer / cer_count)*100:.2f}%" if cer_count > 0 else "N/A", # Legacy
            "avg_inference_rtf": round(total_rtf / rtf_count, 3) if rtf_count > 0 else 0.0,
            "hrs": candidate_stats.get("hrs", 0.0),
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)

def export_markdown_report(results: List[EvaluationResult], summary_path: str, output_path: str):
    """Generates a human-readable Markdown report."""
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    
    lines = [
        "# LLM-based Hallucination Evaluation Report\n",
        f"- **Run Directory**: `{summary['run_dir']}`",
        f"- **Model Used**: `{summary['model_used']}`",
        f"- **Hallucination Rate (All Files - Silence/Noise Included)**: {summary.get('hallucination_rate_all_files', 0.0)*100:.2f}%",
        f"- **Hallucination Rate (Speech Only - Silence/Noise Excluded)**: {summary.get('hallucination_rate_speech_only', 0.0)*100:.2f}%",
        f"- **Average CER (All Files - Silence/Noise Included)**: {summary['existing_metrics'].get('avg_cer_all_files', 'N/A')}",
        f"- **Average CER (Speech Only - Silence/Noise Excluded)**: {summary['existing_metrics'].get('avg_cer_speech_only', 'N/A')}",
        f"- **Manual Review Rate**: {summary['manual_review_rate']*100:.2f}%\n",
        "## Statistics\n",
        "### Error Type Distribution",
        "| Error Type | Count |",
        "| :--- | :--- |"
    ]
    for err, count in summary["error_distribution"].items():
        lines.append(f"| {err} | {count} |")
        
    lines.append("\n### Severity Distribution")
    lines.append("| Severity | Count |")
    lines.append("| :--- | :--- |")
    for sev, count in summary["severity_distribution"].items():
        lines.append(f"| {sev} | {count} |")
        
    lines.append("\n## Detailed Results\n")
    lines.append("| File | Hallucination | Error Type | Severity | CER | Review |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for r in results:
        h_icon = "❌ Yes" if r.has_hallucination else "✅ No"
        review_icon = "👀 Manual" if r.review_status == "manual_review" else "🤖 Auto"
        lines.append(f"| `{r.filename}` | {h_icon} | {r.primary_error} | {r.severity} | {r.existing_cer or 'N/A'} | {review_icon} |")
        
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
