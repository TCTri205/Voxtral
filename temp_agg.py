import json
import os

voxtral_base = r"d:\VJ\Voxtral\results"
javis_base = r"d:\VJ\Voxtral\results_javis"
runs = [f"19-04-2026_v{i}" for i in range(1, 11)]

def collect_data(base_path):
    data = []
    for run in runs:
        path = os.path.join(base_path, run, "llm_eval_summary.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data.append(json.load(f))
    return data

voxtral_data = collect_data(voxtral_base)
javis_data = collect_data(javis_base)

def aggregate(data_list):
    total = len(data_list)
    if total == 0: return {}, {}, {}
    avg_metrics = {
        "hallucination_rate": 0,
        "manual_review_rate": 0,
        "avg_cer": 0,
        "avg_inference_rtf": 0
    }
    error_dist = {}
    severity_dist = {}
    
    for d in data_list:
        avg_metrics["hallucination_rate"] += d["hallucination_rate"]
        avg_metrics["manual_review_rate"] += d["manual_review_rate"]
        avg_metrics["avg_cer"] += float(d["existing_metrics"]["avg_cer"].replace('%', ''))
        avg_metrics["avg_inference_rtf"] += d["existing_metrics"]["avg_inference_rtf"]
        
        for k, v in d["error_distribution"].items():
            error_dist[k] = error_dist.get(k, 0) + v
        for k, v in d["severity_distribution"].items():
            severity_dist[k] = severity_dist.get(k, 0) + v
            
    for k in avg_metrics:
        avg_metrics[k] /= total
        
    for k in error_dist:
        error_dist[k] /= total
    for k in severity_dist:
        severity_dist[k] /= total
        
    # Format CER and RTF
    avg_metrics["avg_cer"] = f"{avg_metrics['avg_cer']:.2f}%"
    avg_metrics["avg_inference_rtf"] = f"{avg_metrics['avg_inference_rtf']:.4f}"
    
    return avg_metrics, error_dist, severity_dist

v_metrics, v_error, v_severity = aggregate(voxtral_data)
j_metrics, j_error, j_severity = aggregate(javis_data)

results = {
    "voxtral": {"metrics": v_metrics, "error": v_error, "severity": v_severity},
    "javis": {"metrics": j_metrics, "error": j_error, "severity": j_severity}
}

with open(r"d:\VJ\Voxtral\temp_results.json", 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
