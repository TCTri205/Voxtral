
import librosa
import numpy as np
import json
import os

def analyze_audio(file_path):
    try:
        # Load audio (automatically converts to mono if needed)
        y, sr = librosa.load(file_path, sr=None)
        
        # Calculate RMS over windows
        window_size = int(sr * 0.1) # 100ms
        hop_length = window_size
        rms_frames = librosa.feature.rms(y=y, frame_length=window_size, hop_length=hop_length)[0]
        
        avg_rms = np.mean(rms_frames)
        max_rms = np.max(rms_frames)
        
        # Estimate Noise Floor (lowest 10% of RMS)
        sorted_rms = np.sort(rms_frames)
        noise_floor = np.mean(sorted_rms[:max(1, int(len(sorted_rms)*0.1))])
        
        # SNR estimate (approximate)
        snr = 20 * np.log10(avg_rms / max(1e-6, noise_floor))
        
        # Dynamic range
        dynamic_range = 20 * np.log10(max_rms / max(1e-6, noise_floor))
        
        # Crest Factor
        crest_factor = 20 * np.log10(max_rms / max(1e-6, avg_rms))

        return {
            "file": os.path.basename(file_path),
            "avg_rms": float(avg_rms),
            "max_rms": float(max_rms),
            "noise_floor": float(noise_floor),
            "snr_db": float(snr),
            "dynamic_range_db": float(dynamic_range),
            "crest_factor_db": float(crest_factor),
            "duration": float(len(y) / sr)
        }
    except Exception as e:
        return {"file": os.path.basename(file_path), "error": str(e)}

files = [
    "d:/VJ/Voxtral/audio/media_148280_1767762915627.mp3",
    "d:/VJ/Voxtral/audio/media_149733_1769589919400.mp3",
    "d:/VJ/Voxtral/audio/media_148284_1767766514646 (1).mp3",
    "d:/VJ/Voxtral/audio/media_148393_1767860211615 (1).mp3",
    "d:/VJ/Voxtral/audio/media_148394_1767860189485 (1).mp3",
    "d:/VJ/Voxtral/audio/media_148414_1767922241264 (1).mp3"
]

results = []
for f in files:
    results.append(analyze_audio(f))

print(json.dumps(results, indent=4))
