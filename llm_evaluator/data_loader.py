import json
import os
from pathlib import Path
from typing import List, Dict, Any
from .schema import EvaluationCandidate
from .voxtral_utils import canonical_stem

def load_results(results_json_path: str) -> List[Dict[str, Any]]:
    """Loads results.json and returns successful records."""
    if not os.path.exists(results_json_path):
        return []
    with open(results_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [r for r in data if r.get("status") == "success"]

def load_ground_truth_map(ground_truth_path: str) -> Dict[str, str]:
    """Loads ground_truth.json and maps canonical_id to text."""
    if not os.path.exists(ground_truth_path):
        return {}
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {canonical_stem(k): v for k, v in data.items()}

def load_timestamp_map(timestamps_dir: str) -> Dict[str, str]:
    """Loads all *.txt files in timestamps_dir and maps canonical_id to content."""
    if not os.path.isdir(timestamps_dir):
        return {}
    ts_map = {}
    for f in Path(timestamps_dir).glob("*.txt"):
        try:
            content = f.read_text(encoding="utf-8")
            ts_map[canonical_stem(f.name)] = content
        except Exception:
            continue
    return ts_map

def load_evaluation_candidates(
    results_json_path: str,
    ground_truth_path: str = "ground_truth.json",
    timestamps_dir: str = "timestamps"
) -> List[EvaluationCandidate]:
    """
    Main entry for loading candidates. Matches results with GT sources.
    """
    results = load_results(results_json_path)
    gt_plain_map = load_ground_truth_map(ground_truth_path)
    gt_ts_map = load_timestamp_map(timestamps_dir)
    
    candidates = []
    for res in results:
        fname = res.get("file", "")
        if not fname:
            continue
            
        c_id = canonical_stem(fname)
        
        candidate = EvaluationCandidate(
            filename=fname,
            canonical_id=c_id,
            hyp_transcript=res.get("transcript", ""),
            gt_timestamped=gt_ts_map.get(c_id),
            gt_plain=gt_plain_map.get(c_id),
            duration=res.get("duration"),
            existing_cer=res.get("cer"),
            existing_rf=res.get("rf", 0),
            existing_inference_rtf=res.get("inference_rtf")
        )
        candidates.append(candidate)
        
    return candidates
