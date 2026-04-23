import csv
import os
import json

voxtral_base = r"d:\VJ\Voxtral\results"
javis_base = r"d:\VJ\Voxtral\results_javis"
runs = [f"19-04-2026_v{i}" for i in range(1, 11)]

def collect_per_file_details(base_path):
    all_files_data = {}
    for run in runs:
        path = os.path.join(base_path, run, "llm_eval_details.csv")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row or 'filename' not in row:
                        continue
                    fname = row['filename']
                    if not fname: continue
                    
                    if fname not in all_files_data:
                        all_files_data[fname] = {}
                    
                    # Convert hallucination to symbol
                    h = "H" if row['has_hallucination'].lower() == 'true' else "OK"
                    cer = row['existing_cer']
                    
                    all_files_data[fname][run] = f"{h} ({cer})"
    return all_files_data

v_details = collect_per_file_details(voxtral_base)
j_details = collect_per_file_details(javis_base)

# Flatten for report generation
final_comparison = []
all_filenames = sorted(list(set(list(v_details.keys()) + list(j_details.keys()))))

for fname in all_filenames:
    v_row = {"file": fname, "system": "Voxtral"}
    j_row = {"file": fname, "system": "Javis"}
    for run in runs:
        v_row[run] = v_details.get(fname, {}).get(run, "-")
        j_row[run] = j_details.get(fname, {}).get(run, "-")
    final_comparison.append(v_row)
    final_comparison.append(j_row)

with open(r"d:\VJ\Voxtral\per_file_results.json", 'w', encoding='utf-8') as f:
    json.dump(final_comparison, f, indent=2)
print("SUCCESS: Data written to per_file_results.json")
