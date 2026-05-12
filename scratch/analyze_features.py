import librosa
import numpy as np

def analyze_start(file_path):
    y, sr = librosa.load(file_path, sr=16000, duration=5)
    
    # Analyze every 100ms
    hop_length = int(0.1 * sr)
    
    # RMS Energy
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    
    # Spectral Flatness (higher means more noise-like)
    flatness = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]
    
    # Zero Crossing Rate (high ZCR often means noise or fricatives)
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    
    print("Time | Energy | Flatness | ZCR | Type")
    print("-" * 40)
    for i in range(len(rms)):
        t = i * 0.1
        e = rms[i]
        f = flatness[i]
        z = zcr[i]
        
        # Heuristic for speech vs noise
        # Speech usually has lower flatness and moderate energy
        # Noise usually has higher flatness
        atype = "Silence"
        if e > 0.01:
            if f > 0.1:
                atype = "Noise/Fricative"
            else:
                atype = "Voice-like"
        
        print(f"{t:.1f}s | {e:.4f} | {f:.4f} | {z:.4f} | {atype}")

if __name__ == "__main__":
    path = r"D:\VJ\Voxtral\audio\media_148414_1767922241264 (1).mp3"
    analyze_start(path)
