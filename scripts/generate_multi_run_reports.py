import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
RESULT_ROOTS = {
    "voxtral": PROJECT_ROOT / "results",
    "javis": PROJECT_ROOT / "results_javis",
}
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_DATA_DIR = REPORTS_DIR / "data"
TIMESTAMPS_DIR = PROJECT_ROOT / "timestamps"
RTTM_DIR = PROJECT_ROOT / "rttm"
AUDIO_QUALITY_PATH = PROJECT_ROOT / "audio_quality_analysis.json"
SNAPSHOT_DATE = str(date.today())

SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "unknown": -1}
CASE_STUDY_FILES = [
    ("voxtral", "media_148414_1767922241264 (1).mp3", "Sai ngôn ngữ hoặc sai hoàn toàn (Language Error or Absolute Failure)"),
    ("javis", "media_148439_1767926711644 (1).mp3", "Looping hoặc thay thế nội dung (Looping or Content Replacement)"),
    ("voxtral", "media_149291_1769069811005.mp3", "Bỏ sót hoặc ngắt sớm (Omission or Early Truncation)"),
    ("javis", "media_148394_1767860189485 (1).mp3", "Giữ cấu trúc tốt hơn ở narrowband (Structure Preservation in Narrowband)"),
]
REPORT_BANNED_NUMBERS = ["38.27%", "34.24%", "152.73%"]


@dataclass(frozen=True)
class RunInfo:
    engine: str
    run_id: str
    path: Path
    sort_key: tuple[int, int, int, int]


def parse_run_sort_key(run_id: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})_v(\d+)", run_id)
    if not match:
        return (0, 0, 0, 0)
    day, month, year, version = match.groups()
    return (int(year), int(month), int(day), int(version))


def parse_percent(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return None


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    frac = index - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def bootstrap_mean_ci(values: list[float], seed: int) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(2000):
        resample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        samples.append(statistics.mean(resample))
    samples.sort()
    return (percentile(samples, 0.025), percentile(samples, 0.975))


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = (
        z
        * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
        / denom
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def pairwise_probability(
    left_values: list[float],
    right_values: list[float],
    *,
    comparator: str,
) -> tuple[float, float, float]:
    total_pairs = len(left_values) * len(right_values)
    if total_pairs == 0:
        return (float("nan"), float("nan"), float("nan"))
    left_wins = 0
    ties = 0
    for left in left_values:
        for right in right_values:
            if comparator == "lt":
                if left < right:
                    left_wins += 1
                elif left == right:
                    ties += 1
            else:
                raise ValueError(f"Unsupported comparator: {comparator}")
    left_probability = left_wins / total_pairs
    tie_probability = ties / total_pairs
    right_probability = (total_pairs - left_wins - ties) / total_pairs
    return (left_probability, right_probability, tie_probability)


def bootstrap_pairwise_probability_ci(
    left_values: list[float],
    right_values: list[float],
    *,
    comparator: str,
    seed: int,
) -> tuple[float, float]:
    if not left_values or not right_values:
        return (float("nan"), float("nan"))
    if len(left_values) == 1 and len(right_values) == 1:
        _, right_probability, _ = pairwise_probability(left_values, right_values, comparator=comparator)
        return (right_probability, right_probability)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(2000):
        left_sample = [left_values[rng.randrange(len(left_values))] for _ in range(len(left_values))]
        right_sample = [right_values[rng.randrange(len(right_values))] for _ in range(len(right_values))]
        _, right_probability, _ = pairwise_probability(left_sample, right_sample, comparator=comparator)
        samples.append(right_probability)
    samples.sort()
    return (percentile(samples, 0.025), percentile(samples, 0.975))


def quality_tier(cer: float | None) -> str:
    if cer is None:
        return "unknown"
    if cer <= 20:
        return "good"
    if cer <= 50:
        return "fair"
    return "poor"


def format_float(value: float | None, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{digits}f}"


def format_percent(value: float | None, digits: int = 1) -> str:
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{digits}f}%"


def format_ci_percent(ci: tuple[float, float], digits: int = 1) -> str:
    low, high = ci
    return f"{format_percent(low * 100, digits)} đến {format_percent(high * 100, digits)}"


def format_ci_float(ci: tuple[float, float], digits: int = 3) -> str:
    low, high = ci
    return f"{format_float(low, digits)} đến {format_float(high, digits)}"


def transcript_hash(transcript: str) -> str:
    return hashlib.sha256(transcript.encode("utf-8")).hexdigest()[:12]


def load_audio_quality() -> dict[str, dict]:
    data = json.loads(AUDIO_QUALITY_PATH.read_text(encoding="utf-8"))
    return {entry["file"]: entry for entry in data}


def load_llm_details(path: Path) -> dict[str, dict]:
    details: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            details[row["filename"]] = row
    return details


def find_timestamp_path(file_name: str) -> Path | None:
    stem = Path(file_name).stem
    candidates = [
        TIMESTAMPS_DIR / f"{stem}.txt",
        TIMESTAMPS_DIR / f"{stem.replace(' (1)', '_(1)')}.txt",
        TIMESTAMPS_DIR / f"{stem.replace('_(1)', ' (1)')}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_rttm_path(file_name: str) -> Path | None:
    stem = Path(file_name).stem
    candidates = [
        RTTM_DIR / f"{stem}.rttm",
        RTTM_DIR / f"{stem.replace(' (1)', '')}.rttm",
        RTTM_DIR / f"{stem.replace('_(1)', '')}.rttm",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def read_timestamp_excerpt(file_name: str, max_lines: int = 3) -> str:
    path = find_timestamp_path(file_name)
    if path is None:
        return "Không có transcript timestamped cho file này."
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return " ".join(lines[:max_lines]) if lines else "Timestamp file rỗng."


def parse_rttm_stats(file_name: str) -> dict[str, int | float | str]:
    path = find_rttm_path(file_name)
    if path is None:
        return {"segments": 0, "speakers": 0, "voiced_seconds": 0.0, "path": ""}
    segments = 0
    speakers = set()
    voiced = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        segments += 1
        speakers.add(parts[7])
        try:
            voiced += float(parts[4])
        except ValueError:
            continue
    return {
        "segments": segments,
        "speakers": len(speakers),
        "voiced_seconds": voiced,
        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def discover_runs() -> dict[str, list[RunInfo]]:
    runs: dict[str, list[RunInfo]] = {}
    for engine, root in RESULT_ROOTS.items():
        infos: list[RunInfo] = []
        for path in root.iterdir():
            if path.is_dir() and path.name.startswith(tuple("0123456789")):
                infos.append(
                    RunInfo(
                        engine=engine,
                        run_id=path.name,
                        path=path,
                        sort_key=parse_run_sort_key(path.name),
                    )
                )
        runs[engine] = sorted(infos, key=lambda item: item.sort_key)
    return runs


def build_dataset() -> tuple[list[dict], dict]:
    audio_quality = load_audio_quality()
    runs = discover_runs()
    records: list[dict] = []
    latest_run_by_engine = {engine: engine_runs[-1] for engine, engine_runs in runs.items()}

    for engine, engine_runs in runs.items():
        for run in engine_runs:
            results = json.loads((run.path / "results.json").read_text(encoding="utf-8"))
            llm_details = load_llm_details(run.path / "llm_eval_details.csv")
            llm_summary = json.loads((run.path / "llm_eval_summary.json").read_text(encoding="utf-8"))
            for item in results:
                file_name = item["file"]
                llm_row = llm_details.get(file_name, {})
                audio_row = audio_quality.get(file_name, {})
                record = {
                    "engine": engine,
                    "run_id": run.run_id,
                    "run_sort_key": run.sort_key,
                    "file": file_name,
                    "status": item.get("status", ""),
                    "duration": item.get("duration"),
                    "rf": item.get("rf"),
                    "cer": parse_percent(item.get("cer")),
                    "inference_rtf": parse_percent(item.get("inference_rtf")),
                    "transcript": item.get("transcript", ""),
                    "transcript_hash": transcript_hash(item.get("transcript", "")),
                    "transcript_length": len(item.get("transcript", "")),
                    "llm_has_hallucination": llm_row.get("has_hallucination") == "True",
                    "llm_primary_error": llm_row.get("primary_error", "unknown"),
                    "llm_severity": llm_row.get("severity", "unknown"),
                    "llm_confidence": llm_row.get("confidence", "unknown"),
                    "llm_review_status": llm_row.get("review_status", "unknown"),
                    "llm_reasoning": llm_row.get("reasoning", ""),
                    "llm_evidence_hyp_text": llm_row.get("evidence_hyp_text", ""),
                    "llm_evidence_gt_context": llm_row.get("evidence_gt_context", ""),
                    "audio_avg_rms": audio_row.get("avg_rms"),
                    "audio_max_rms": audio_row.get("max_rms"),
                    "audio_avg_flatness": audio_row.get("avg_flatness"),
                    "audio_avg_centroid": audio_row.get("avg_centroid"),
                    "audio_avg_rolloff": audio_row.get("avg_rolloff"),
                    "audio_reasons": audio_row.get("reasons", []),
                    "has_timestamp": find_timestamp_path(file_name) is not None,
                    "has_rttm": find_rttm_path(file_name) is not None,
                    "llm_summary_hallucination_rate": llm_summary.get("hallucination_rate"),
                }
                records.append(record)

    metadata = {
        "snapshot_date": SNAPSHOT_DATE,
        "runs": {engine: [run.run_id for run in engine_runs] for engine, engine_runs in runs.items()},
        "latest_runs": {engine: info.run_id for engine, info in latest_run_by_engine.items()},
    }
    return records, metadata


def group_records(records: Iterable[dict], *keys: str) -> dict[tuple, list[dict]]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        grouped[tuple(record[key] for key in keys)].append(record)
    return grouped


def summarize_metric(values: list[float], seed: int) -> dict:
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "p95": percentile(values, 0.95),
        "mean_ci95": bootstrap_mean_ci(values, seed),
    }


def build_summary(records: list[dict], metadata: dict) -> dict:
    by_engine = group_records(records, "engine")
    by_engine_file = group_records(records, "engine", "file")
    by_engine_run = group_records(records, "engine", "run_id")
    files = sorted({record["file"] for record in records})
    timestamped_files = sorted({record["file"] for record in records if record["has_timestamp"]})

    engine_summary: dict[str, dict] = {}
    engine_file_summary: dict[str, dict] = {}
    engine_run_summary: dict[str, dict] = {}

    for engine, engine_records in by_engine.items():
        engine_name = engine[0]
        cer_values = [record["cer"] for record in engine_records if record["cer"] is not None]
        rtf_values = [record["inference_rtf"] for record in engine_records if record["inference_rtf"] is not None]
        cer_gt_values = [record["cer"] for record in engine_records if record["file"] in timestamped_files and record["cer"] is not None]
        hall_successes = sum(1 for record in engine_records if record["llm_has_hallucination"])
        high_successes = sum(1 for record in engine_records if record["llm_severity"] == "high")
        engine_summary[engine_name] = {
            "records": len(engine_records),
            "runs": len({record["run_id"] for record in engine_records}),
            "files": len({record["file"] for record in engine_records}),
            "timestamped_files": len({record["file"] for record in engine_records if record["has_timestamp"]}),
            "cer_all": summarize_metric(cer_values, seed=101 + len(engine_name)),
            "cer_gt": summarize_metric(cer_gt_values, seed=301 + len(engine_name)),
            "rtf": summarize_metric(rtf_values, seed=501 + len(engine_name)),
            "hallucination_rate": hall_successes / len(engine_records),
            "hallucination_rate_ci95": wilson_ci(hall_successes, len(engine_records)),
            "high_severity_rate": high_successes / len(engine_records),
            "high_severity_rate_ci95": wilson_ci(high_successes, len(engine_records)),
            "status_counts": dict(Counter(record["status"] for record in engine_records)),
        }

        file_rows: dict[str, dict] = {}
        for (group_engine, file_name), file_records in by_engine_file.items():
            if group_engine != engine_name:
                continue
            cer_values = [record["cer"] for record in file_records if record["cer"] is not None]
            rtf_values = [record["inference_rtf"] for record in file_records if record["inference_rtf"] is not None]
            severity_counts = Counter(record["llm_severity"] for record in file_records)
            primary_error_counts = Counter(record["llm_primary_error"] for record in file_records)
            transcript_hashes = Counter(record["transcript_hash"] for record in file_records)
            file_rows[file_name] = {
                "runs": len(file_records),
                "cer_mean": statistics.mean(cer_values),
                "cer_std": statistics.pstdev(cer_values) if len(cer_values) > 1 else 0.0,
                "cer_min": min(cer_values),
                "cer_max": max(cer_values),
                "rtf_mean": statistics.mean(rtf_values),
                "rtf_std": statistics.pstdev(rtf_values) if len(rtf_values) > 1 else 0.0,
                "hallucination_rate": sum(1 for record in file_records if record["llm_has_hallucination"]) / len(file_records),
                "high_severity_rate": sum(1 for record in file_records if record["llm_severity"] == "high") / len(file_records),
                "severity_counts": dict(severity_counts),
                "primary_error_counts": dict(primary_error_counts),
                "distinct_cer_values": len({record["cer"] for record in file_records}),
                "distinct_transcript_hashes": len(transcript_hashes),
                "quality_tiers": dict(Counter(quality_tier(record["cer"]) for record in file_records)),
                "quality_tier_changes": len({quality_tier(record["cer"]) for record in file_records}) > 1,
                "representative_hash": transcript_hashes.most_common(1)[0][0],
                "audio": {
                    "avg_rolloff": file_records[0]["audio_avg_rolloff"],
                    "avg_flatness": file_records[0]["audio_avg_flatness"],
                    "avg_rms": file_records[0]["audio_avg_rms"],
                    "max_rms": file_records[0]["audio_max_rms"],
                    "reasons": file_records[0]["audio_reasons"],
                },
                "timestamp_excerpt": read_timestamp_excerpt(file_name),
                "rttm": parse_rttm_stats(file_name),
            }
        engine_file_summary[engine_name] = file_rows

        run_rows: dict[str, dict] = {}
        for (group_engine, run_id), run_records in by_engine_run.items():
            if group_engine != engine_name:
                continue
            run_rows[run_id] = {
                "mean_cer_all": statistics.mean(record["cer"] for record in run_records if record["cer"] is not None),
                "mean_cer_gt": statistics.mean(
                    record["cer"]
                    for record in run_records
                    if record["file"] in timestamped_files and record["cer"] is not None
                ),
                "mean_rtf": statistics.mean(record["inference_rtf"] for record in run_records if record["inference_rtf"] is not None),
                "hallucination_rate": sum(1 for record in run_records if record["llm_has_hallucination"]) / len(run_records),
            }
        engine_run_summary[engine_name] = run_rows

    comparison = {
        "files": {},
        "run_level": {},
    }
    voxtral_runs = list(engine_run_summary["voxtral"].values())
    javis_runs = list(engine_run_summary["javis"].values())
    voxtral_run_cer = [row["mean_cer_all"] for row in voxtral_runs]
    javis_run_cer = [row["mean_cer_all"] for row in javis_runs]
    voxtral_run_rtf = [row["mean_rtf"] for row in voxtral_runs]
    javis_run_rtf = [row["mean_rtf"] for row in javis_runs]
    vox_cer_prob, javis_cer_prob, tie_cer_prob = pairwise_probability(voxtral_run_cer, javis_run_cer, comparator="lt")
    vox_rtf_prob, javis_rtf_prob, tie_rtf_prob = pairwise_probability(voxtral_run_rtf, javis_run_rtf, comparator="lt")
    total_run_pairs = len(voxtral_runs) * len(javis_runs)
    comparison["run_level"] = {
        "total_pairs": total_run_pairs,
        "voxtral_better_cer_probability": vox_cer_prob,
        "javis_better_cer_probability": javis_cer_prob,
        "tie_cer_probability": tie_cer_prob,
        "voxtral_faster_probability": vox_rtf_prob,
        "javis_faster_probability": javis_rtf_prob,
        "tie_rtf_probability": tie_rtf_prob,
        "javis_better_cer_ci95": bootstrap_pairwise_probability_ci(
            voxtral_run_cer,
            javis_run_cer,
            comparator="lt",
            seed=701,
        ),
        "javis_faster_ci95": bootstrap_pairwise_probability_ci(
            voxtral_run_rtf,
            javis_run_rtf,
            comparator="lt",
            seed=702,
        ),
    }

    for file_name in files:
        vox_records = by_engine_file[("voxtral", file_name)]
        javis_records = by_engine_file[("javis", file_name)]
        vox_cers = [record["cer"] for record in vox_records]
        javis_cers = [record["cer"] for record in javis_records]
        vox_better, javis_better, ties = pairwise_probability(vox_cers, javis_cers, comparator="lt")
        total_pairs = len(vox_records) * len(javis_records)
        comparison["files"][file_name] = {
            "voxtral_cer_mean": engine_file_summary["voxtral"][file_name]["cer_mean"],
            "javis_cer_mean": engine_file_summary["javis"][file_name]["cer_mean"],
            "voxtral_rtf_mean": engine_file_summary["voxtral"][file_name]["rtf_mean"],
            "javis_rtf_mean": engine_file_summary["javis"][file_name]["rtf_mean"],
            "voxtral_better_probability": vox_better,
            "javis_better_probability": javis_better,
            "tie_probability": ties,
            "javis_better_ci95": bootstrap_pairwise_probability_ci(
                vox_cers,
                javis_cers,
                comparator="lt",
                seed=900 + sum(ord(ch) for ch in file_name),
            ),
        }

    poor_cases: list[dict] = []
    for engine, files_summary in engine_file_summary.items():
        cer_means = {file_name: row["cer_mean"] for file_name, row in files_summary.items()}
        cer_stds = {file_name: row["cer_std"] for file_name, row in files_summary.items()}
        high_rates = {file_name: row["high_severity_rate"] for file_name, row in files_summary.items()}
        cer_tail_threshold = percentile(list(cer_means.values()), 0.85)
        std_tail_threshold = percentile(list(cer_stds.values()), 0.85)
        high_tail_threshold = percentile(list(high_rates.values()), 0.85)
        rtf_tail_threshold = percentile([row["rtf_mean"] for row in files_summary.values()], 0.85)

        for file_name, row in files_summary.items():
            if file_name not in timestamped_files and row["cer_mean"] == 0:
                continue
            triggers = []
            if row["cer_mean"] >= 80:
                triggers.append("CER>=80%")
            if row["rtf_mean"] >= 2.0:
                triggers.append("RTF>=2.0")
            if row["high_severity_rate"] > 0:
                triggers.append("Có severity=high")
            if row["cer_std"] >= 10:
                triggers.append("CER std>=10")
            if row["quality_tier_changes"]:
                triggers.append("Đổi hạng chất lượng giữa các run")
            if row["cer_mean"] >= cer_tail_threshold:
                triggers.append("Top tail CER")
            if row["cer_std"] >= std_tail_threshold and row["cer_std"] > 0:
                triggers.append("Top tail bất ổn")
            if row["high_severity_rate"] >= high_tail_threshold and row["high_severity_rate"] > 0:
                triggers.append("Top tail severity high")
            if row["rtf_mean"] >= rtf_tail_threshold:
                triggers.append("Top tail RTF")
            if triggers:
                poor_cases.append(
                    {
                        "engine": engine,
                        "file": file_name,
                        "triggers": triggers,
                        "cer_mean": row["cer_mean"],
                        "cer_std": row["cer_std"],
                        "rtf_mean": row["rtf_mean"],
                        "hallucination_rate": row["hallucination_rate"],
                        "high_severity_rate": row["high_severity_rate"],
                        "distinct_transcript_hashes": row["distinct_transcript_hashes"],
                        "audio_rolloff": row["audio"]["avg_rolloff"],
                        "audio_flatness": row["audio"]["avg_flatness"],
                    }
                )
    poor_cases.sort(key=lambda row: (len(row["triggers"]), row["cer_mean"], row["cer_std"], row["high_severity_rate"]), reverse=True)

    hallucination = {"engine": {}, "file": {}}
    for engine, engine_records in by_engine.items():
        engine_name = engine[0]
        total = len(engine_records)
        hallucination["engine"][engine_name] = {
            "total": total,
            "hallucination_rate": sum(1 for record in engine_records if record["llm_has_hallucination"]) / total,
            "hallucination_rate_ci95": wilson_ci(sum(1 for record in engine_records if record["llm_has_hallucination"]), total),
            "high_severity_rate": sum(1 for record in engine_records if record["llm_severity"] == "high") / total,
            "high_severity_rate_ci95": wilson_ci(sum(1 for record in engine_records if record["llm_severity"] == "high"), total),
            "severity_counts": dict(Counter(record["llm_severity"] for record in engine_records)),
            "primary_error_counts": dict(Counter(record["llm_primary_error"] for record in engine_records)),
        }
    for engine, files_summary in engine_file_summary.items():
        hallucination["file"][engine] = {
            file_name: {
                "hallucination_rate": row["hallucination_rate"],
                "high_severity_rate": row["high_severity_rate"],
                "severity_counts": row["severity_counts"],
                "primary_error_counts": row["primary_error_counts"],
                "distinct_transcript_hashes": row["distinct_transcript_hashes"],
            }
            for file_name, row in files_summary.items()
        }

    summary = {
        "metadata": metadata,
        "files": files,
        "timestamped_files": timestamped_files,
        "engine_summary": engine_summary,
        "engine_file_summary": engine_file_summary,
        "engine_run_summary": engine_run_summary,
        "comparison": comparison,
        "poor_cases": poor_cases,
        "hallucination": hallucination,
    }
    return summary


def escape_pipes(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_records_csv(records: list[dict]) -> None:
    REPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DATA_DIR / "multi_run_records.csv"
    fieldnames = [
        "engine",
        "run_id",
        "file",
        "status",
        "duration",
        "rf",
        "cer",
        "inference_rtf",
        "transcript_hash",
        "transcript_length",
        "llm_has_hallucination",
        "llm_primary_error",
        "llm_severity",
        "llm_confidence",
        "llm_review_status",
        "audio_avg_rms",
        "audio_max_rms",
        "audio_avg_flatness",
        "audio_avg_centroid",
        "audio_avg_rolloff",
        "has_timestamp",
        "has_rttm",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(records, key=lambda row: (row["engine"], row["run_sort_key"], row["file"])):
            writer.writerow({name: record.get(name) for name in fieldnames})


def write_summary_json(summary: dict) -> None:
    REPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DATA_DIR / "multi_run_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def render_data_source_block(summary: dict) -> list[str]:
    runs = summary["metadata"]["runs"]
    records_path = "./data/multi_run_records.csv"
    summary_path = "./data/multi_run_summary.json"
    return [
        "## Nguồn dữ liệu",
        f"- Snapshot date: `{summary['metadata']['snapshot_date']}`",
        f"- Voxtral runs: `{runs['voxtral'][0]}` đến `{runs['voxtral'][-1]}` ({len(runs['voxtral'])} run, thư mục `results/`)",
        f"- Javis runs: `{runs['javis'][0]}` đến `{runs['javis'][-1]}` ({len(runs['javis'])} run, thư mục `results_javis/`)",
        f"- Record count: `{summary['engine_summary']['voxtral']['records'] + summary['engine_summary']['javis']['records']}` inference record trên `{len(summary['files'])}` file",
        f"- Unified snapshot files: [multi_run_records.csv]({records_path}), [multi_run_summary.json]({summary_path})",
        "",
    ]


def render_metrics_report(summary: dict) -> str:
    lines = ["# Báo cáo chỉ số nền (Baseline Metrics Report) - Multi-run", ""]
    lines.extend(render_data_source_block(summary))
    lines.extend(
        [
            "## Phạm vi thống kê (Statistical Scope)",
            f"- CER và RTF được tổng hợp trên toàn bộ record; riêng CER trên file hội thoại có GT timestamped được báo riêng cho `{len(summary['timestamped_files'])}` file.",
            "- Khoảng tin cậy 95% cho mean dùng bootstrap; khoảng tin cậy cho tỷ lệ dùng Wilson interval.",
            "",
            "## Thống kê theo engine (Statistics by Engine)",
            "",
            "| Engine | CER trung bình (Mean CER) | 95% CI | CER trung bình (9 GT) | 95% CI | Trung vị (Median) CER | Độ lệch chuẩn (Std Dev) CER | Min | Max | P95 | RTF trung bình (Mean RTF) | 95% CI | Tỷ lệ ảo giác (Hallucination Rate) | 95% CI | Tỷ lệ nghiêm trọng cao (High Severity Rate) | 95% CI |",
            "| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | --- |",
        ]
    )
    for engine in ("voxtral", "javis"):
        row = summary["engine_summary"][engine]
        lines.append(
            "| "
            + " | ".join(
                [
                    engine,
                    format_percent(row["cer_all"]["mean"]),
                    format_ci_percent((row["cer_all"]["mean_ci95"][0] / 100, row["cer_all"]["mean_ci95"][1] / 100)),
                    format_percent(row["cer_gt"]["mean"]),
                    format_ci_percent((row["cer_gt"]["mean_ci95"][0] / 100, row["cer_gt"]["mean_ci95"][1] / 100)),
                    format_percent(row["cer_all"]["median"]),
                    format_percent(row["cer_all"]["std"]),
                    format_percent(row["cer_all"]["min"]),
                    format_percent(row["cer_all"]["max"]),
                    format_percent(row["cer_all"]["p95"]),
                    format_float(row["rtf"]["mean"], 3),
                    format_ci_float(row["rtf"]["mean_ci95"], 3),
                    format_percent(row["hallucination_rate"] * 100),
                    format_ci_percent(row["hallucination_rate_ci95"]),
                    format_percent(row["high_severity_rate"] * 100),
                    format_ci_percent(row["high_severity_rate_ci95"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Độ ổn định theo run (Stability by Run)", "", "| Engine | CER trung bình (Mean CER) giữa các run | Độ lệch chuẩn (Std Dev) CER theo run | RTF trung bình (Mean RTF) giữa các run | Độ lệch chuẩn (Std Dev) RTF theo run | Ghi chú (Notes) |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for engine in ("voxtral", "javis"):
        run_rows = list(summary["engine_run_summary"][engine].values())
        mean_cers = [row["mean_cer_all"] for row in run_rows]
        mean_rtfs = [row["mean_rtf"] for row in run_rows]
        note = "CER bất biến trên mọi run." if statistics.pstdev(mean_cers) == 0 else "CER thay đổi giữa các run."
        lines.append(
            f"| {engine} | {format_percent(statistics.mean(mean_cers))} | {format_percent(statistics.pstdev(mean_cers))} | {format_float(statistics.mean(mean_rtfs), 3)} | {format_float(statistics.pstdev(mean_rtfs), 3)} | {note} |"
        )

    lines.extend(["", "## File bất ổn nhất (Least Stable Files) theo CER", "", "| Engine | File | CER trung bình (Mean CER) | Độ lệch chuẩn (Std Dev) CER | Số CER duy nhất (Unique CERs) | Số transcript hash duy nhất (Unique hashes) | Đổi hạng chất lượng (Quality Grade Change) |", "| --- | --- | ---: | ---: | ---: | ---: | --- |"])
    top_rows = []
    for engine, files_summary in summary["engine_file_summary"].items():
        for file_name, row in files_summary.items():
            top_rows.append((row["cer_std"], engine, file_name, row))
    for _, engine, file_name, row in sorted(top_rows, reverse=True)[:8]:
        lines.append(
            f"| {engine} | `{file_name}` | {format_percent(row['cer_mean'])} | {format_percent(row['cer_std'])} | {row['distinct_cer_values']} | {row['distinct_transcript_hashes']} | {'Có' if row['quality_tier_changes'] else 'Không'} |"
        )

    lines.extend(
        [
            "",
            "## Quan sát dữ liệu",
            f"- Voxtral có mean CER toàn bộ snapshot là {format_percent(summary['engine_summary']['voxtral']['cer_all']['mean'])}; Javis là {format_percent(summary['engine_summary']['javis']['cer_all']['mean'])}.",
            f"- CER của Voxtral không đổi giữa 15 run, nhưng mean RTF vẫn dao động nhẹ quanh {format_float(summary['engine_summary']['voxtral']['rtf']['mean'], 3)}.",
            f"- Javis nhanh hơn hẳn: mean inference RTF {format_float(summary['engine_summary']['javis']['rtf']['mean'], 3)} với p95 {format_float(summary['engine_summary']['javis']['rtf']['p95'], 3)}.",
            f"- Bất ổn CER tập trung ở Javis, nổi bật nhất là `media_149291_1769069811005.mp3` với std CER {format_percent(summary['engine_file_summary']['javis']['media_149291_1769069811005.mp3']['cer_std'])}.",
            "",
        ]
    )
    return "\n".join(lines)


def render_comparison_report(summary: dict) -> str:
    run_level = summary["comparison"]["run_level"]
    lines = ["# So sánh phân phối (Distribution Comparison) Voxtral và Javis", ""]
    lines.extend(render_data_source_block(summary))
    lines.extend(
        [
            "## So sánh tổng thể (Overall Comparison)",
            "",
            "| Chỉ số (Metrics) | Voxtral | Javis | Quan sát (Observations) |",
            "| --- | ---: | ---: | --- |",
            f"| CER trung bình (11 file) | {format_percent(summary['engine_summary']['voxtral']['cer_all']['mean'])} | {format_percent(summary['engine_summary']['javis']['cer_all']['mean'])} | Javis thấp hơn trên trung bình tổng thể. |",
            f"| CER trung bình (9 GT) | {format_percent(summary['engine_summary']['voxtral']['cer_gt']['mean'])} | {format_percent(summary['engine_summary']['javis']['cer_gt']['mean'])} | Javis vẫn thấp hơn khi bỏ 2 file silence/noise. |",
            f"| RTF trung bình | {format_float(summary['engine_summary']['voxtral']['rtf']['mean'], 3)} | {format_float(summary['engine_summary']['javis']['rtf']['mean'], 3)} | Javis nhanh hơn nhiều bậc. |",
            f"| Tỷ lệ ảo giác | {format_percent(summary['engine_summary']['voxtral']['hallucination_rate'] * 100)} | {format_percent(summary['engine_summary']['javis']['hallucination_rate'] * 100)} | Cả hai đều cao theo LLM-eval; Javis cao hơn trên tần suất thực nghiệm. |",
            f"| Tỷ lệ nghiêm trọng cao | {format_percent(summary['engine_summary']['voxtral']['high_severity_rate'] * 100)} | {format_percent(summary['engine_summary']['javis']['high_severity_rate'] * 100)} | Javis nhỉnh hơn về tần suất severity high. |",
            "",
            "## Xác suất thực nghiệm giữa các run (Empirical Probability between Runs)",
            f"- Nếu lấy ngẫu nhiên 1 run Voxtral và 1 run Javis, xác suất Javis có mean CER thấp hơn là {format_percent(run_level['javis_better_cer_probability'] * 100)}; 95% CI: {format_ci_percent(run_level['javis_better_cer_ci95'])}.",
            f"- Trong cùng phép lấy mẫu đó, xác suất Javis có mean RTF thấp hơn là {format_percent(run_level['javis_faster_probability'] * 100)}; 95% CI: {format_ci_percent(run_level['javis_faster_ci95'])}.",
            "",
            "## Xác suất thắng theo từng file (Win Probability by File)",
            "",
            "| File | CER trung bình (Mean CER) Voxtral | CER trung bình (Mean CER) Javis | P(Javis CER < Voxtral CER) | 95% CI (Confidence Interval) | Kết luận (Conclusion) |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for file_name, row in sorted(
        summary["comparison"]["files"].items(),
        key=lambda item: item[1]["javis_better_probability"],
        reverse=True,
    ):
        if row["javis_better_probability"] > row["voxtral_better_probability"]:
            winner = "Javis có lợi thế"
        elif row["javis_better_probability"] < row["voxtral_better_probability"]:
            winner = "Voxtral có lợi thế"
        else:
            winner = "Hòa"
        lines.append(
            f"| `{file_name}` | {format_percent(row['voxtral_cer_mean'])} | {format_percent(row['javis_cer_mean'])} | {format_percent(row['javis_better_probability'] * 100)} | {format_ci_percent(row['javis_better_ci95'])} | {winner} |"
        )

    lines.extend(
        [
            "",
            "## Quan sát dữ liệu",
            "- Voxtral thắng chắc trên `media_148284_1767766514646 (1).mp3` và `media_148393_1767860211615 (1).mp3`; Javis thắng chắc trên `media_148394_1767860189485 (1).mp3` và `media_148414_1767922241264 (1).mp3`.",
            "- `media_149291_1769069811005.mp3` là file cân bằng nhất về CER giữa hai engine do Javis dao động rất mạnh giữa các run.",
            "- Hai file `silence_60s.wav` và `stochastic_noise_60s.wav` không phân thắng thua về CER vì cả hai đều ghi 0.00% trong snapshot hiện dùng.",
            "",
        ]
    )
    return "\n".join(lines)


def render_poor_cases_report(summary: dict) -> str:
    lines = ["# Các trường hợp (Cases) ASR xấu theo ngưỡng cứng (Hard Thresholds) và Tail", ""]
    lines.extend(render_data_source_block(summary))
    lines.extend(
        [
            "## Tiêu chí chọn case xấu (Criteria for Poor Case Selection)",
            "- Ngưỡng cứng: `CER >= 80%`, `RTF >= 2.0`, có `severity=high`, `std CER >= 10`, hoặc đổi hạng chất lượng giữa các run.",
            "- Tail ranking: top 15% theo mean CER, mean RTF, std CER, hoặc high-severity rate trong từng engine.",
            "",
            "## Danh sách ưu tiên (Priority List)",
            "",
            "| Engine | File | Trigger | CER trung bình (Mean CER) | Độ lệch chuẩn (Std Dev) CER | RTF trung bình (Mean RTF) | Tỷ lệ ảo giác (Hallucination Rate) | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Số transcript hash duy nhất (Unique hashes) | Audio rolloff (Hz) |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["poor_cases"][:12]:
        lines.append(
            f"| {row['engine']} | `{row['file']}` | {escape_pipes(', '.join(row['triggers']))} | {format_percent(row['cer_mean'])} | {format_percent(row['cer_std'])} | {format_float(row['rtf_mean'], 3)} | {format_percent(row['hallucination_rate'] * 100)} | {format_percent(row['high_severity_rate'] * 100)} | {row['distinct_transcript_hashes']} | {format_float(row['audio_rolloff'], 0)} |"
        )

    lines.extend(["", "## Quan sát dữ liệu", ""])
    top_vox = [row for row in summary["poor_cases"] if row["engine"] == "voxtral"][:4]
    top_javis = [row for row in summary["poor_cases"] if row["engine"] == "javis"][:4]
    for row in top_vox + top_javis:
        lines.append(
            f"- `{row['engine']} / {row['file']}` nổi bật vì {', '.join(row['triggers'][:3])}; mean CER {format_percent(row['cer_mean'])}, std CER {format_percent(row['cer_std'])}, rolloff {format_float(row['audio_rolloff'], 0)} Hz."
        )

    lines.extend(
        [
            "",
            "## Giả thuyết kỹ thuật (Technical Hypotheses)",
            "- Các file có rolloff quanh 1.9 kHz đến 2.4 kHz nhiều khả năng thuộc narrowband telephony; đây là một tương quan quan sát được, không phải bằng chứng nhân quả đầy đủ.",
            "- Ở Javis, số lượng transcript hash khác nhau cao trên cùng một file gợi ý thành phần decoder hoặc streaming path có biến thiên giữa các run.",
            "- Ở Voxtral, các case xấu không đến từ dao động run-to-run mà đến từ một lỗi có tính lặp lại trên cùng loại đầu vào.",
            "",
        ]
    )
    return "\n".join(lines)


def render_hallucination_report(summary: dict) -> str:
    lines = ["# Hallucination analysis (Phân tích ảo giác) - Multi-run", ""]
    lines.extend(render_data_source_block(summary))
    lines.extend(
        [
            "## Tần suất thực nghiệm theo engine (Empirical Frequency by Engine)",
            "",
            "| Engine | Tỷ lệ ảo giác (Hallucination Rate) | 95% CI | Tỷ lệ nghiêm trọng cao (High Severity Rate) | 95% CI | Loại lỗi chính (Primary Error Type) |",
            "| --- | ---: | --- | ---: | --- | --- |",
        ]
    )
    for engine in ("voxtral", "javis"):
        row = summary["hallucination"]["engine"][engine]
        primary_error = max(row["primary_error_counts"].items(), key=lambda item: item[1])[0]
        lines.append(
            f"| {engine} | {format_percent(row['hallucination_rate'] * 100)} | {format_ci_percent(row['hallucination_rate_ci95'])} | {format_percent(row['high_severity_rate'] * 100)} | {format_ci_percent(row['high_severity_rate_ci95'])} | `{primary_error}` |"
        )

    lines.extend(["", "## Phân bổ mức độ (Severity Distribution)", "", "| Engine | none | low | medium | high |", "| --- | ---: | ---: | ---: | ---: |"])
    for engine in ("voxtral", "javis"):
        row = summary["hallucination"]["engine"][engine]["severity_counts"]
        lines.append(
            f"| {engine} | {row.get('none', 0)} | {row.get('low', 0)} | {row.get('medium', 0)} | {row.get('high', 0)} |"
        )

    lines.extend(["", "## File có rủi ro nghiêm trọng cao nhất (Files with Highest High Severity Risk)", "", "| Engine | File | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Tỷ lệ ảo giác (Hallucination Rate) | Loại lỗi hỗn hợp chính (Primary Mixed Error Types) |", "| --- | --- | ---: | ---: | --- |"])
    file_rows = []
    artifact_rows = []
    for engine, files_summary in summary["hallucination"]["file"].items():
        for file_name, row in files_summary.items():
            error_mix = ", ".join(
                f"{name}:{count}" for name, count in sorted(row["primary_error_counts"].items(), key=lambda item: (-item[1], item[0]))
            )
            item = (row["high_severity_rate"], engine, file_name, row["hallucination_rate"], error_mix, row["distinct_transcript_hashes"])
            if file_name in {"silence_60s.wav", "stochastic_noise_60s.wav"}:
                artifact_rows.append(item)
            elif row["high_severity_rate"] > 0:
                file_rows.append(item)
    for _, engine, file_name, hall_rate, error_mix, distinct_hashes in sorted(file_rows, reverse=True)[:10]:
        lines.append(
            f"| {engine} | `{file_name}` | {format_percent(_ * 100)} | {format_percent(hall_rate * 100)} | {escape_pipes(error_mix)}; hash={distinct_hashes} |"
        )

    lines.extend(["", "## Silence/noise evaluator artifacts", "", "| Engine | File | Tỷ lệ nghiêm trọng cao (High Severity Rate) | Tỷ lệ ảo giác (Hallucination Rate) | Loại lỗi hỗn hợp chính (Primary Mixed Error Types) | Ghi chú |", "| --- | --- | ---: | ---: | --- | --- |"])
    for _, engine, file_name, hall_rate, error_mix, distinct_hashes in sorted(artifact_rows, reverse=True):
        lines.append(
            f"| {engine} | `{file_name}` | {format_percent(_ * 100)} | {format_percent(hall_rate * 100)} | {escape_pipes(error_mix)}; hash={distinct_hashes} | Không đưa vào bảng chính vì CER của file này bằng 0.00%. |"
        )

    lines.extend(
        [
            "",
            "## Quan sát dữ liệu",
            "- Javis có hallucination rate cao hơn Voxtral trên snapshot này, nhưng phần lớn dưới dạng insertion/content replacement thay vì một mode lỗi duy nhất.",
            "- `silence_60s.wav` và `stochastic_noise_60s.wav` được tách riêng thành nhóm artifact của evaluator, vì chúng không đại diện cho lỗi nhận dạng hội thoại thông thường.",
            "- `silence_60s.wav` bị gắn `silence_text` lặp lại ở cả hai engine trong nhiều run, vì vậy cần coi đây là tín hiệu của lớp evaluator chứ không phải bằng chứng tuyệt đối về đầu ra sai.",
            "- Vì lý do đó, các file silence/noise với CER = 0.00% không được đưa vào bảng high-severity chính.",
            "- Với Voxtral, transcript hash theo file là bất biến giữa các run nhưng nhãn LLM-eval vẫn dao động ở một số file; điều này cho thấy tầng đánh giá có độ nhiễu riêng.",
            "",
            "## Giả thuyết kỹ thuật (Technical Hypotheses)",
            "- Khi hypothesis giữ nguyên mà nhãn severity thay đổi, biến thiên nhiều khả năng đến từ LLM evaluator hoặc prompt framing, không đến từ ASR engine.",
            "- Các file narrowband có xu hướng xuất hiện insertion nhiều hơn, phù hợp với giả thuyết decoder cố lấp khoảng trống bằng chuỗi quen thuộc.",
            "",
        ]
    )
    return "\n".join(lines)


def choose_representative_record(records: list[dict], engine: str, file_name: str, mode: str) -> dict:
    candidates = [record for record in records if record["engine"] == engine and record["file"] == file_name]
    if mode == "max_cer":
        return max(candidates, key=lambda row: (row["cer"], row["run_sort_key"]))
    if mode == "min_cer":
        return min(candidates, key=lambda row: (row["cer"], row["run_sort_key"]))
    if mode == "latest":
        return max(candidates, key=lambda row: row["run_sort_key"])
    return candidates[0]


def render_case_section(summary: dict, records: list[dict], engine: str, file_name: str, label: str) -> list[str]:
    file_summary = summary["engine_file_summary"][engine][file_name]
    comparison = summary["comparison"]["files"][file_name]
    mode = "max_cer" if engine == "javis" and "Looping" in label else "latest"
    record = choose_representative_record(records, engine, file_name, mode)
    counterpart_engine = "javis" if engine == "voxtral" else "voxtral"
    counterpart = summary["engine_file_summary"][counterpart_engine][file_name]
    gt_excerpt = file_summary["timestamp_excerpt"]
    hyp_excerpt = record["llm_evidence_hyp_text"] or "(không có excerpt ngắn trong llm_eval)"
    rttm = file_summary["rttm"]
    winner_probability = comparison["javis_better_probability"] if counterpart_engine == "javis" else comparison["voxtral_better_probability"]
    section = [
        f"## {label}: `{file_name}`",
        "",
        "### Quan sát dữ liệu (Data Observations)",
        f"- Engine trọng tâm: `{engine}`; mean CER {format_percent(file_summary['cer_mean'])}, std CER {format_percent(file_summary['cer_std'])}, mean RTF {format_float(file_summary['rtf_mean'], 3)}.",
        f"- Engine đối chứng `{counterpart_engine}` có mean CER {format_percent(counterpart['cer_mean'])}. Xác suất `{counterpart_engine}` tốt hơn về CER trên file này là {format_percent(winner_probability * 100)}.",
        f"- LLM-eval trên `{engine}`: hallucination rate {format_percent(file_summary['hallucination_rate'] * 100)}, high severity rate {format_percent(file_summary['high_severity_rate'] * 100)}.",
        f"- Audio quality: rolloff {format_float(file_summary['audio']['avg_rolloff'], 0)} Hz, flatness {format_float(file_summary['audio']['avg_flatness'], 3)}, RMS trung bình {format_float(file_summary['audio']['avg_rms'], 3)}.",
        f"- RTTM: {rttm['segments']} segment, {rttm['speakers']} speaker, khoảng {format_float(float(rttm['voiced_seconds']), 1)} giây có thoại trong `{rttm['path'] or 'N/A'}`.",
        f"- GT excerpt: {gt_excerpt}",
        f"- Hypothesis excerpt dùng minh họa: {hyp_excerpt}",
        "",
        "### Giả thuyết kỹ thuật (Technical Hypotheses)",
    ]
    if file_name == "media_148414_1767922241264 (1).mp3":
        section.extend(
            [
                "- Đây là một lỗi có tính lặp lại của Voxtral trên file narrowband này, vì transcript hash bất biến qua mọi run và CER cố định 100.00%.",
                "- Việc hypothesis rơi sang một câu tiếng Anh rất ngắn gợi ý failure mode nhận dạng sai ngôn ngữ hoặc collapse decoder; đây là suy luận từ đầu ra, không phải fact về kiến trúc nội bộ.",
            ]
        )
    elif file_name == "media_148439_1767926711644 (1).mp3":
        section.extend(
            [
                "- Javis có nhiều transcript hash khác nhau trên file này và xuất hiện các run CER rất cao, phù hợp với failure mode looping hoặc drift nội dung.",
                "- Sự chênh lệch lớn giữa các run cho thấy đây không phải lỗi tất định của riêng file, mà là lỗi có xác suất xảy ra khi điều kiện giải mã xấu.",
            ]
        )
    elif file_name == "media_149291_1769069811005.mp3":
        section.extend(
            [
                "- Voxtral chỉ tạo một hypothesis ngắn trong khi file có thời lượng thoại lớn, nên giả thuyết hợp lý nhất là ngắt sớm hoặc bỏ sót phần lớn nội dung.",
                "- File này cũng cho thấy Javis có tail risk lớn: mean CER gần ngang Voxtral nhưng variance rất cao, nên không thể chỉ đọc trung bình mà kết luận ổn định.",
            ]
        )
    else:
        section.extend(
            [
                "- Trên file narrowband này, Javis giữ cấu trúc hội thoại gần GT hơn Voxtral ở phần lớn run, dù vẫn có insertion mức medium.",
                "- Rolloff thấp hỗ trợ giả thuyết rằng băng thông hẹp làm Voxtral suy giảm mạnh hơn về cấu trúc, nhưng đây vẫn chỉ là tương quan quan sát được trong snapshot.",
            ]
        )
    section.append("")
    return section


def render_detailed_timestamp_report(summary: dict, records: list[dict]) -> str:
    lines = ["# Phụ lục (Appendix): Case study có timestamp (Timeline Case Studies)", ""]
    lines.extend(render_data_source_block(summary))
    lines.extend(
        [
            "## Nguyên tắc chọn case (Case Selection Criteria)",
            "- Chỉ chọn các file xuất hiện trong thống kê tổng thể và có `timestamps/` cùng `rttm/` để truy vết.",
            "- File này không tự tạo metric mới; mọi số liệu đều lấy từ snapshot liên-run trong `reports/data/`.",
            "",
        ]
    )
    for engine, file_name, label in CASE_STUDY_FILES:
        lines.extend(render_case_section(summary, records, engine, file_name, label))
    return "\n".join(lines)


def write_report(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def validate_outputs(summary: dict) -> None:
    for file_name in [
        "metrics.md",
        "comparison.md",
        "poor_asr_cases.md",
        "hallucination_analysis.md",
        "detailed_timestamp_analysis.md",
    ]:
        text = (REPORTS_DIR / file_name).read_text(encoding="utf-8")
        for banned in REPORT_BANNED_NUMBERS:
            if banned in text:
                raise ValueError(f"Found banned legacy number {banned} in {file_name}")
        if "ảo giác tiếng Hàn" in text:
            raise ValueError(f"Found unsupported phrase in {file_name}")
        if "## Nguồn dữ liệu" not in text:
            raise ValueError(f"Missing data source section in {file_name}")

    voxtral_mean = format_percent(summary["engine_summary"]["voxtral"]["cer_all"]["mean"])
    javis_mean = format_percent(summary["engine_summary"]["javis"]["cer_all"]["mean"])
    metrics_text = (REPORTS_DIR / "metrics.md").read_text(encoding="utf-8")
    comparison_text = (REPORTS_DIR / "comparison.md").read_text(encoding="utf-8")
    if voxtral_mean not in metrics_text or javis_mean not in metrics_text:
        raise ValueError("metrics.md does not contain snapshot mean CER values")
    if voxtral_mean not in comparison_text or javis_mean not in comparison_text:
        raise ValueError("comparison.md does not contain snapshot mean CER values")


def main() -> None:
    records, metadata = build_dataset()
    summary = build_summary(records, metadata)
    write_records_csv(records)
    write_summary_json(summary)

    write_report(REPORTS_DIR / "metrics.md", render_metrics_report(summary))
    write_report(REPORTS_DIR / "comparison.md", render_comparison_report(summary))
    write_report(REPORTS_DIR / "poor_asr_cases.md", render_poor_cases_report(summary))
    write_report(REPORTS_DIR / "hallucination_analysis.md", render_hallucination_report(summary))
    write_report(REPORTS_DIR / "detailed_timestamp_analysis.md", render_detailed_timestamp_report(summary, records))
    validate_outputs(summary)


if __name__ == "__main__":
    main()
