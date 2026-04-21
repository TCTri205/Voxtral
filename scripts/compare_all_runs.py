import json
import os
from pathlib import Path
from collections import defaultdict

def compare_results(results_dir):
    results_dir = Path(results_dir)
    run_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    
    all_runs_data = {}
    for run_dir in run_dirs:
        results_file = run_dir / "results.json"
        if results_file.exists():
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    all_runs_data[run_dir.name] = json.load(f)
            except Exception as e:
                print(f"Error reading {results_file}: {e}")

    if not all_runs_data:
        print("No results.json files found.")
        return

    run_names = sorted(all_runs_data.keys())
    print(f"Found {len(run_names)} runs to compare: {', '.join(run_names)}")

    # Map filename -> {run_name -> data}
    file_map = defaultdict(dict)
    for run_name, data in all_runs_data.items():
        for entry in data:
            if "file" in entry:
                file_map[entry["file"]][run_name] = entry

    all_files = sorted(file_map.keys())
    
    # Analyze fields
    common_fields = set()
    first_run = run_names[0]
    first_data = all_runs_data[first_run]
    if first_data:
        common_fields = set(first_data[0].keys())

    stability_report = defaultdict(lambda: {"identical_count": 0, "different_count": 0, "values_seen": defaultdict(set)})

    for filename in all_files:
        entries = file_map[filename]
        
        # Check if file is present in all runs
        missing_runs = [run for run in run_names if run not in entries]
        if missing_runs:
            print(f"File {filename} is missing in: {', '.join(missing_runs)}")

        # Compare fields across available runs
        available_runs = [run for run in run_names if run in entries]
        if not available_runs: continue
        
        first_entry = entries[available_runs[0]]
        fields = set(first_entry.keys())
        
        for field in fields:
            values = [str(entries[run].get(field)) for run in available_runs]
            unique_values = set(values)
            if len(unique_values) == 1:
                stability_report[field]["identical_count"] += 1
            else:
                stability_report[field]["different_count"] += 1
                stability_report[field]["values_seen"][filename] = unique_values

    print("\n--- Field Stability Analysis ---")
    print(f"{'Field':<20} | {'Identical':<10} | {'Different':<10} | {'Status'}")
    print("-" * 60)
    for field in sorted(stability_report.keys()):
        identical = stability_report[field]["identical_count"]
        different = stability_report[field]["different_count"]
        status = "PERFECTLY STABLE" if different == 0 else "VOLATILE"
        print(f"{field:<20} | {identical:<10} | {different:<10} | {status}")

    print("\n--- Conclusion ---")
    is_completely_identical = all(v["different_count"] == 0 for v in stability_report.values())
    if is_completely_identical:
        print("All files are COMPLETELY IDENTICAL across all runs.")
    else:
        print("Files are NOT identical. Some fields vary across runs.")
        
    stable_fields = [f for f, v in stability_report.items() if v["different_count"] == 0]
    volatile_fields = [f for f, v in stability_report.items() if v["different_count"] > 0]
    
    print(f"Stable fields (consistent): {', '.join(stable_fields)}")
    print(f"Volatile fields (vary): {', '.join(volatile_fields)}")

if __name__ == "__main__":
    compare_results("d:/VJ/Voxtral/results")
