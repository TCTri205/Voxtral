import re
import os
from pathlib import Path

def normalize_japanese(text):
    """
    Normalizes Japanese text for CER calculation and semantic comparison.
    1. Removes Japanese and Western punctuation.
    2. Removes all spaces.
    3. Converts Full-width alphanumeric to Half-width.
    """
    if not text:
        return ""
    # 1. Remove Japanese and Western punctuation
    # 、 。 ! ? ( ) ... 「 」 , . : ; [ ] { }
    text = re.sub(r'[、。！？（）…「」,. :;\[\]{}()\'"]', '', text)
    
    # 2. Remove all spaces
    text = "".join(text.split())
    
    # 3. Full-width to Half-width for alphanumeric (basic implementation)
    # Full-width: 0xFF01 (!) to 0xFF5E (~) maps to 0x0021 to 0x007E
    chars = []
    for c in text:
        code = ord(c)
        if 0xFF01 <= code <= 0xFF5E:
            chars.append(chr(code - 0xFEE0))
        elif code == 0x3000: # Full-width space
            pass
        else:
            chars.append(c)
    return "".join(chars).lower()

def calculate_hrs(results: list[dict], silence_keywords=["silence", "white_noise", "noise"]) -> float:
    """
    Hallucination Rate on Silence (HRS) = chars_generated / total_silence_minutes.
    Shared utility for evaluate_metrics.py and llm_evaluator.
    """
    total_chars = 0
    total_seconds = 0
    
    for res in results:
        fname = res.get("file", "").lower()
        if any(kw in fname for kw in silence_keywords):
            text = res.get("transcript", "")
            total_chars += len(text)
            total_seconds += res.get("duration", 0)
            
    if total_seconds == 0:
        return 0.0
    
    minutes = total_seconds / 60
    return total_chars / minutes

def canonical_stem(path_or_name: str) -> str:
    """
    Generates a canonical stem for file matching.
    Follows rules: remove extension, lowercase, replace non-alphanumeric with _,
    merge multiple underscores, and strip from ends.
    """
    if not path_or_name:
        return ""
    
    # 1. Get basename and remove extension
    stem = Path(path_or_name).stem.lower()
    
    # 2. Replace everything not a-z0-9 with _
    stem = re.sub(r'[^a-z0-9]', '_', stem)
    
    # 3. Merge multiple underscores
    stem = re.sub(r'_+', '_', stem)
    
    # 4. Strip underscores from ends
    stem = stem.strip('_')
    
    return stem

def calculate_rf(text, n=3):
    """Repetition Factor (RF) using Window-based N-gram."""
    if not text or len(text) < n:
        return 0
    
    # Simple character-based N-gram for Japanese
    ngrams = [text[i:i+n] for i in range(len(text)-n+1)]
    
    repeats = 0
    consecutive_count = 1
    max_consecutive = 1
    
    for i in range(len(ngrams)-1):
        if ngrams[i] == ngrams[i+1]:
            consecutive_count += 1
            max_consecutive = max(max_consecutive, consecutive_count)
        else:
            if consecutive_count >= 3:
                repeats += 1
            consecutive_count = 1
            
    # Check last one
    if consecutive_count >= 3:
        repeats += 1
        
    return repeats

def calculate_cer(hyp, ref):
    """Character Error Rate calculation."""
    n = len(hyp)
    m = len(ref)
    if m == 0: return 1.0 if n > 0 else 0.0
    
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if hyp[i-1] == ref[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
                
    return dp[n][m] / m
