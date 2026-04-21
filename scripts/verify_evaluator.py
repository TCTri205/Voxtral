import os
import sys
import json
from pathlib import Path

# Add project root to path so we can import llm_evaluator
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from llm_evaluator.voxtral_utils import canonical_stem, calculate_hrs
from llm_evaluator.data_loader import load_evaluation_candidates

def test_canonical_stem():
    print("Testing canonical_stem...")
    test_cases = {
        "media_148284_1767766514646 (1).mp3": "media_148284_1767766514646_1",
        "media_148284_1767766514646_(1).txt": "media_148284_1767766514646_1",
        "Some File (Test).wav": "some_file_test",
        "Already_Clean": "already_clean",
        "---Multiple---Dashes---": "multiple_dashes"
    }
    
    for input_name, expected in test_cases.items():
        result = canonical_stem(input_name)
        assert result == expected, f"Failed: {input_name} -> {result} (expected {expected})"
        print(f"  OK: {input_name} -> {result}")

def test_calculate_hrs():
    print("Testing calculate_hrs...")
    mock_results = [
        {"file": "silence_test.mp3", "transcript": "Hello world", "duration": 60.0}, # 11 chars, 1 min
        {"file": "normal.mp3", "transcript": "ignore me", "duration": 30.0},
        {"file": "noise_bg.wav", "transcript": "Repeating", "duration": 120.0}, # 9 chars, 2 mins
    ]
    # Total chars in silence: 11 + 9 = 20
    # Total silence duration: 60 + 120 = 180s = 3 mins
    # HRS = 20 / 3 = 6.666...
    
    hrs = calculate_hrs(mock_results)
    assert abs(hrs - 6.6666) < 0.001, f"Failed: HRS calculation {hrs}"
    print(f"  OK: HRS = {hrs:.4f}")

def test_data_loader_matching():
    # This requires existing results/17-04-2026_v2 or similar
    # We'll just check if current setup matches something known or skip if not available
    results_path = "results/17-04-2026_v2/results.json"
    if os.path.exists(results_path):
        print(f"Testing data_loader matching on {results_path}...")
        candidates = load_evaluation_candidates(
            results_json_path=results_path,
            ground_truth_path="ground_truth.json",
            timestamps_dir="timestamps"
        )
        print(f"  Found {len(candidates)} candidates.")
        for c in candidates:
            has_gt = "YES" if c.gt_timestamped else "NO"
            print(f"    {c.filename} -> Canonical: {c.canonical_id} | GT: {has_gt}")
    else:
        print(f"Skipping data_loader test (file not found: {results_path})")

if __name__ == "__main__":
    try:
        test_canonical_stem()
        test_calculate_hrs()
        test_data_loader_matching()
        print("\nALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        sys.exit(1)
