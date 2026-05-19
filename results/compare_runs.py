import json
import os
import sys
import difflib
from pathlib import Path

# Paths
V4_PATH = Path("d:/VJ/Voxtral/results/18-05-2026_v4/results.json")
V6_PATH = Path("d:/VJ/Voxtral/results/18-05-2026_v6/results.json")
GT_PATH = Path("d:/VJ/Voxtral/ground_truth.json")
OUTPUT_MD_PATH = Path("d:/VJ/Voxtral/results/comparison_output.md")

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_text(text):
    return "".join(text.split()).lower()

def show_diff(ref, hyp):
    d = difflib.Differ()
    diff = list(d.compare(ref, hyp))
    result = []
    for char in diff:
        if char.startswith('  '):
            result.append(char[2:])
        elif char.startswith('- '):
            result.append(f"[-{char[2:]}]")
        elif char.startswith('+ '):
            result.append(f"[+{char[2:]}]")
    return "".join(result)

def main():
    v4 = load_json(V4_PATH)
    v6 = load_json(V6_PATH)
    gt = load_json(GT_PATH)

    if not v4 or not v6 or not gt:
        print("Failed to load JSON files.")
        return

    # Index by file
    v4_map = {item["file"]: item for item in v4}
    v6_map = {item["file"]: item for item in v6}

    all_files = sorted(list(set(v4_map.keys()) | set(v6_map.keys())))

    lines = []
    def out(s):
        lines.append(s)

    out("# Voxtral Run Comparison: V4 vs V6")
    out(f"- **V4 Config (v11)**: Threshold = {v4[0].get('vad_config', {}).get('VAD_THRESHOLD', 'N/A')}")
    out(f"- **V6 Config (v12)**: Threshold = {v6[0].get('vad_config', {}).get('VAD_THRESHOLD', 'N/A')}")
    out("")

    worse_files = []
    better_files = []
    same_files = []

    # Pre-parse results to group them
    for fname in all_files:
        item4 = v4_map.get(fname)
        item6 = v6_map.get(fname)
        ref_text = gt.get(fname, "")

        if not item4 or not item6:
            continue

        # Parse CER
        def parse_cer(cer_str):
            if not cer_str or cer_str == "N/A":
                return None
            try:
                num = cer_str.split("%")[0].strip()
                return float(num)
            except:
                return None

        cer4 = parse_cer(item4.get("cer"))
        cer6 = parse_cer(item6.get("cer"))

        tx4 = item4.get("transcript", "")
        tx6 = item6.get("transcript", "")

        if cer4 is None or cer6 is None:
            continue

        diff_cer = cer6 - cer4
        if abs(diff_cer) < 0.01 and tx4 == tx6:
            same_files.append((fname, cer4, cer6))
            continue

        if diff_cer > 0.01:
            worse_files.append((fname, cer4, cer6, diff_cer, tx4, tx6, ref_text, item4, item6))
        elif diff_cer < -0.01:
            better_files.append((fname, cer4, cer6, diff_cer, tx4, tx6, ref_text, item4, item6))
        else:
            same_files.append((fname, cer4, cer6))

    out("## SUMMARY STATS")
    out(f"- **Total files compared**: {len(all_files)}")
    out(f"- **Files with identical CER & text**: {len(same_files)}")
    out(f"- **Files that got BETTER in V6**: {len(better_files)}")
    out(f"- **Files that got WORSE in V6**: {len(worse_files)}")
    out("")

    out("### Worse in V6 List")
    for f in worse_files:
        out(f"- `{f[0]}`: {f[1]:.2f}% -> {f[2]:.2f}% ({f[3]:+.2f}%)")
    out("")

    out("### Better in V6 List")
    for f in better_files:
        out(f"- `{f[0]}`: {f[1]:.2f}% -> {f[2]:.2f}% ({f[3]:+.2f}%)")
    out("")

    out("## DETAILED FILE-BY-FILE ANALYSIS")
    out("")

    def process_file_section(f, status_label):
        fname, cer4, cer6, diff_cer, tx4, tx6, ref_text, item4, item6 = f
        out(f"### `{fname}` ({status_label})")
        out(f"- **CER V4**: {cer4:.2f}% | **CER V6**: {cer6:.2f}% (change of **{diff_cer:+.2f}%**)")
        out(f"- **RTF V4**: {item4.get('inference_rtf', 0.0):.3f} | **RTF V6**: {item6.get('inference_rtf', 0.0):.3f}")
        
        vad4 = item4.get("vad_result", {})
        vad6 = item6.get("vad_result", {})
        out(f"- **VAD Trim V4**: {vad4.get('original_duration', 0.0):.2f}s -> {vad4.get('trimmed_duration', 0.0):.2f}s (Speech: {vad4.get('speech_detected', False)})")
        out(f"- **VAD Trim V6**: {vad6.get('original_duration', 0.0):.2f}s -> {vad6.get('trimmed_duration', 0.0):.2f}s (Speech: {vad6.get('speech_detected', False)})")
        out("")
        out("**Ground Truth:**")
        out(f"> {ref_text}")
        out("")
        out("**V4 Transcript:**")
        out(f"> {tx4}")
        out("")
        out("**V6 Transcript:**")
        out(f"> {tx6}")
        out("")
        out("**GT vs V4 Diff:**")
        out(f"`{show_diff(ref_text, tx4)}`")
        out("")
        out("**GT vs V6 Diff:**")
        out(f"`{show_diff(ref_text, tx6)}`")
        out("")
        
        # Output chunk telemetry if exists
        tel4 = item4.get("chunk_telemetry", [])
        tel6 = item6.get("chunk_telemetry", [])
        out("**Chunk Telemetry comparison:**")
        out("| Chunk | V4 Start-End | V4 Duration | V4 RTF | V4 Retries | V6 Start-End | V6 Duration | V6 RTF | V6 Retries | V6 Skipped |")
        out("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        
        max_chunks = max(len(tel4), len(tel6))
        for idx in range(max_chunks):
            ch4 = tel4[idx] if idx < len(tel4) else {}
            ch6 = tel6[idx] if idx < len(tel6) else {}
            
            c_idx = idx + 1
            v4_se = f"{ch4.get('start_sec', 0.0):.1f}-{ch4.get('end_sec', 0.0):.1f}" if ch4 else "-"
            v4_dur = f"{ch4.get('duration', 0.0):.2f}s" if ch4 else "-"
            v4_rtf = f"{ch4.get('inference_rtf', 0.0):.2f}" if ch4 else "-"
            v4_ret = f"{ch4.get('retry_count', 0)}" if ch4 else "-"
            
            v6_se = f"{ch6.get('start_sec', 0.0):.1f}-{ch6.get('end_sec', 0.0):.1f}" if ch6 else "-"
            v6_dur = f"{ch6.get('duration', 0.0):.2f}s" if ch6 else "-"
            v6_rtf = f"{ch6.get('inference_rtf', 0.0):.2f}" if ch6 else "-"
            v6_ret = f"{ch6.get('retry_count', 0)}" if ch6 else "-"
            v6_skip = "Yes" if (ch6 and ch6.get('duration', 0.0) > 0 and ch6.get('elapsed', 0.0) == 0.0 and ch6.get('transcript_len', 0) == 0) else "No"
            
            out(f"| {c_idx} | {v4_se} | {v4_dur} | {v4_rtf} | {v4_ret} | {v6_se} | {v6_dur} | {v6_rtf} | {v6_ret} | {v6_skip} |")
        out("\n" + "="*80 + "\n")

    out("### WORSE FILES DETAILED")
    out("")
    for f in worse_files:
        process_file_section(f, "WORSE IN V6")

    out("### BETTER FILES DETAILED")
    out("")
    for f in better_files:
        process_file_section(f, "BETTER IN V6")

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Comparison Markdown successfully saved to: {OUTPUT_MD_PATH}")

if __name__ == "__main__":
    main()
