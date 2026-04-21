from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()


raise SystemExit(
    "scripts/fix_vllm_error.py is deprecated. "
    "Use scripts/update_nb_t4.py instead; it applies the current Voxtral notebook fixes "
    "for dependency preflight, runtime-staleness detection, and T4-safe attention backend selection."
)
