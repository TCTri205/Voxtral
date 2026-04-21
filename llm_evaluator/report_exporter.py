import csv
import json
import os
from typing import List, Dict, Any
from .schema import EvaluationResult

def parse_cer(cer_str: str | None) -> float | None:
    """Parses CER string like '65.49%' to float 0.6549."""
    if not cer_str or cer_str == "N/A":
        return None
    try:
        val = float(cer_str.replace("%", "").strip())
        return val / 100.0
    except ValueError:
        return None

def apply_heuristics(results: List[EvaluationResult]) -> List[EvaluationResult]:
    """Applies heuristic overrides to evaluation results."""
    for res in results:
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
    
    error_dist = {}
    severity_dist = {}
    total_cer = 0.0
    cer_count = 0
    total_rtf = 0.0
    rtf_count = 0
    
    for r in results:
        error_dist[r.primary_error] = error_dist.get(r.primary_error, 0) + 1
        severity_dist[r.severity] = severity_dist.get(r.severity, 0) + 1
        
        cer = parse_cer(r.existing_cer)
        if cer is not None:
            total_cer += cer
            cer_count += 1
            
        if r.existing_inference_rtf is not None:
            total_rtf += r.existing_inference_rtf
            rtf_count += 1

    summary = {
        "run_dir": run_dir,
        "model_used": model_used,
        "total_files": total,
        "evaluated_files": total,
        "with_gt_timestamped": candidate_stats.get("with_gt_timestamped", 0),
        "without_gt_timestamped": candidate_stats.get("without_gt_timestamped", 0),
        "hallucination_rate": round(hallucinated / total, 4) if total > 0 else 0,
        "manual_review_rate": round(manual_review / total, 4) if total > 0 else 0,
        "error_distribution": error_dist,
        "severity_distribution": severity_dist,
        "existing_metrics": {
            "avg_cer": f"{(total_cer / cer_count)*100:.2f}%" if cer_count > 0 else "N/A",
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
        f"- **Hallucination Rate**: {summary['hallucination_rate']*100:.2f}%",
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
