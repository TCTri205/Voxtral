import os
import librosa
import numpy as np
import json
from pathlib import Path

def analyze_audio(file_path):
    print(f"Analyzing {file_path}...")
    try:
        y, sr = librosa.load(file_path, sr=None)
        
        # 1. Volume (RMS)
        rms = librosa.feature.rms(y=y)
        avg_rms = np.mean(rms)
        max_rms = np.max(rms)
        
        # 2. Noise/Distortion (Spectral Flatness & ZCR)
        flatness = librosa.feature.spectral_flatness(y=y)
        avg_flatness = np.mean(flatness)
        
        zcr = librosa.feature.zero_crossing_rate(y)
        avg_zcr = np.mean(zcr)
        
        # 3. Bandwidth (Spectral Centroid & Roll-off)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_centroid = np.mean(centroid)
        
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)
        avg_rolloff = np.mean(rolloff)
        
        # Peak Frequency (Rough estimate of bandwidth)
        S = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        avg_spectrum = np.mean(S, axis=1)
        peak_freq = freqs[np.argmax(avg_spectrum)]
        
        # Determine specific causes based on thresholds (heuristic)
        reasons = []
        if avg_rms < 0.01:
            reasons.append("âm thanh bị nhỏ (low volume)")
        if avg_flatness > 0.1 or avg_zcr > 0.15:
            reasons.append("âm thanh bị rè (noisy/distorted)")
        if avg_rolloff < 4000:
            reasons.append("bandwidth hẹp (low bandwidth)")
            
        return {
            "file": os.path.basename(file_path),
            "avg_rms": float(avg_rms),
            "max_rms": float(max_rms),
            "avg_flatness": float(avg_flatness),
            "avg_centroid": float(avg_centroid),
            "avg_rolloff": float(avg_rolloff),
            "reasons": reasons
        }
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return None

def main():
    audio_dir = "audio"
    results = []
    
    for ext in ["*.mp3", "*.wav"]:
        for file_path in Path(audio_dir).glob(ext):
            analysis = analyze_audio(str(file_path))
            if analysis:
                results.append(analysis)
                
    with open("audio_quality_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\nAnalysis complete. Results saved to audio_quality_analysis.json")

if __name__ == "__main__":
    main()
