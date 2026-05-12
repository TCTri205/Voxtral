import librosa
import numpy as np
import sys

def analyze_audio(file_path):
    print(f"Analyzing {file_path}...")
    try:
        # Load audio (first 10 seconds to check the beginning)
        y, sr = librosa.load(file_path, sr=16000, duration=10)
        
        # Calculate duration
        duration = len(y) / sr
        print(f"Loaded {duration:.2f} seconds of audio.")
        
        # Check volume (RMS) in small windows
        window_size = int(0.1 * sr) # 100ms
        rms = librosa.feature.rms(y=y, frame_length=window_size, hop_length=window_size)[0]
        
        # Check for silence at the very beginning
        # Silero VAD threshold is 0.5, but let's just check raw energy
        print("\nEnergy distribution in first 5 seconds (every 200ms):")
        for i in range(min(25, len(rms))):
            time_sec = i * 0.1
            energy = rms[i]
            status = "SPEECH?" if energy > 0.01 else "SILENCE/NOISE"
            print(f"{time_sec:.1f}s: Energy={energy:.5f} -> {status}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    path = r"D:\VJ\Voxtral\audio\media_148414_1767922241264 (1).mp3"
    analyze_audio(path)
