"""
Comprehensive audio analysis script for media_148414_1767922241264 (1).mp3
Analyzes: metadata, waveform, energy, spectral features, VAD, segmentation.
"""
import os
import sys
import json
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path

AUDIO_PATH = r"d:\VJ\Voxtral\audio\media_148414_1767922241264 (1).mp3"
OUTPUT_DIR = r"d:\VJ\Voxtral\audio\148414"
ANALYSIS_OUT = os.path.join(OUTPUT_DIR, "analysis_report.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def analyze():
    report = {}

    # ========== 1. Load at native sample rate ==========
    y_native, sr_native = librosa.load(AUDIO_PATH, sr=None)
    report["native"] = {
        "sample_rate": int(sr_native),
        "duration_s": round(len(y_native) / sr_native, 3),
        "samples": len(y_native),
        "max_amplitude": round(float(np.max(np.abs(y_native))), 6),
        "mean_amplitude": round(float(np.mean(np.abs(y_native))), 6),
        "rms": round(float(np.sqrt(np.mean(y_native**2))), 6),
    }
    print(f"[1/7] Native audio: SR={sr_native}, dur={report['native']['duration_s']}s, "
          f"maxAmp={report['native']['max_amplitude']}, rms={report['native']['rms']}")

    # ========== 2. Resample to 16kHz (matching server pipeline) ==========
    y_16k = librosa.resample(y_native, orig_sr=sr_native, target_sr=16000)
    sr = 16000
    report["resampled_16k"] = {
        "sample_rate": sr,
        "samples": len(y_16k),
        "duration_s": round(len(y_16k) / sr, 3),
        "max_amplitude": round(float(np.max(np.abs(y_16k))), 6),
        "rms": round(float(np.sqrt(np.mean(y_16k**2))), 6),
    }
    print(f"[2/7] Resampled to 16kHz: {len(y_16k)} samples, dur={report['resampled_16k']['duration_s']}s")

    # ========== 3. Energy analysis in 1-second windows ==========
    hop_s = 1.0
    hop_samples = int(hop_s * sr)
    n_windows = len(y_16k) // hop_samples
    energy_windows = []
    for i in range(n_windows + 1):
        start = i * hop_samples
        end = min((i + 1) * hop_samples, len(y_16k))
        if start >= len(y_16k):
            break
        window = y_16k[start:end]
        rms = float(np.sqrt(np.mean(window**2)))
        max_amp = float(np.max(np.abs(window)))
        energy_windows.append({
            "time_s": round(i * hop_s, 1),
            "rms": round(rms, 6),
            "max_amp": round(max_amp, 6),
            "db": round(20 * np.log10(rms + 1e-10), 2),
        })
    report["energy_per_second"] = energy_windows
    print(f"[3/7] Energy analysis: {len(energy_windows)} windows")

    # Print energy summary
    rms_values = [w["rms"] for w in energy_windows]
    db_values = [w["db"] for w in energy_windows]
    print(f"       RMS range: {min(rms_values):.6f} - {max(rms_values):.6f}")
    print(f"       dB range:  {min(db_values):.2f} - {max(db_values):.2f} dB")

    # ========== 4. Spectral analysis ==========
    # Mel spectrogram for overall characterization
    mel_spec = librosa.feature.melspectrogram(y=y_16k, sr=sr, n_mels=128, hop_length=512)
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    report["spectral"] = {
        "mel_spec_shape": list(mel_spec.shape),
        "mel_db_range": [round(float(mel_db.min()), 2), round(float(mel_db.max()), 2)],
    }

    # Spectral centroid over time
    centroid = librosa.feature.spectral_centroid(y=y_16k, sr=sr, hop_length=512)[0]
    report["spectral"]["centroid_mean_hz"] = round(float(np.mean(centroid)), 2)
    report["spectral"]["centroid_std_hz"] = round(float(np.std(centroid)), 2)
    print(f"[4/7] Spectral: centroid_mean={report['spectral']['centroid_mean_hz']}Hz, "
          f"mel_db_range={report['spectral']['mel_db_range']}")

    # ========== 5. Zero crossing rate (speech vs noise indicator) ==========
    zcr = librosa.feature.zero_crossing_rate(y_16k, frame_length=2048, hop_length=512)[0]
    report["zcr"] = {
        "mean": round(float(np.mean(zcr)), 6),
        "std": round(float(np.std(zcr)), 6),
    }
    print(f"[5/7] ZCR: mean={report['zcr']['mean']}, std={report['zcr']['std']}")

    # ========== 6. Simple energy-based VAD ==========
    # Classify each 1s window as speech/silence
    # Use a threshold based on the overall signal
    overall_rms = float(np.sqrt(np.mean(y_16k**2)))
    silence_threshold_rms = overall_rms * 0.3
    silence_threshold_db = 20 * np.log10(silence_threshold_rms + 1e-10)

    vad_results = []
    for w in energy_windows:
        is_speech = w["rms"] > silence_threshold_rms
        vad_results.append({
            "time_s": w["time_s"],
            "rms": w["rms"],
            "db": w["db"],
            "is_speech": is_speech,
        })

    speech_seconds = sum(1 for v in vad_results if v["is_speech"])
    silence_seconds = sum(1 for v in vad_results if not v["is_speech"])
    report["simple_vad"] = {
        "threshold_rms": round(silence_threshold_rms, 6),
        "threshold_db": round(silence_threshold_db, 2),
        "speech_seconds": speech_seconds,
        "silence_seconds": silence_seconds,
        "per_second": vad_results,
    }
    print(f"[6/7] Simple VAD: speech={speech_seconds}s, silence={silence_seconds}s "
          f"(threshold_rms={silence_threshold_rms:.6f})")

    # ========== 7. Segment the audio ==========
    # Strategy: split into 5-second segments + one remaining
    segment_duration_s = 5.0
    segment_samples = int(segment_duration_s * sr)
    segments = []
    seg_idx = 0
    pos = 0
    while pos < len(y_16k):
        end = min(pos + segment_samples, len(y_16k))
        seg = y_16k[pos:end]
        seg_name = f"segment_{seg_idx:02d}_{round(pos/sr, 1)}s-{round(end/sr, 1)}s.wav"
        seg_path = os.path.join(OUTPUT_DIR, seg_name)
        sf.write(seg_path, seg, sr)

        seg_rms = float(np.sqrt(np.mean(seg**2)))
        seg_max = float(np.max(np.abs(seg)))
        segments.append({
            "index": seg_idx,
            "filename": seg_name,
            "start_s": round(pos / sr, 1),
            "end_s": round(end / sr, 1),
            "duration_s": round((end - pos) / sr, 3),
            "rms": round(seg_rms, 6),
            "max_amp": round(seg_max, 6),
            "db": round(20 * np.log10(seg_rms + 1e-10), 2),
        })
        seg_idx += 1
        pos = end

    report["segments"] = segments
    print(f"[7/7] Segmented into {len(segments)} files in {OUTPUT_DIR}")

    # Also save the full file as WAV at 16kHz for Colab testing
    full_wav_path = os.path.join(OUTPUT_DIR, "full_16khz.wav")
    sf.write(full_wav_path, y_16k, sr)
    print(f"       Full 16kHz WAV saved: {full_wav_path}")

    # Also simulate what the server does: int16 conversion roundtrip
    y_int16 = (y_16k * 32767).astype(np.int16)
    y_roundtrip = y_int16.astype(np.float32) / 32767.0
    roundtrip_diff = np.max(np.abs(y_16k - y_roundtrip))
    report["int16_roundtrip"] = {
        "max_diff": round(float(roundtrip_diff), 8),
        "note": "Difference from float32->int16->float32 conversion (server pipeline)",
    }
    roundtrip_wav_path = os.path.join(OUTPUT_DIR, "full_16khz_int16_roundtrip.wav")
    sf.write(roundtrip_wav_path, y_roundtrip, sr)
    print(f"       Int16 roundtrip WAV saved: {roundtrip_wav_path}")
    print(f"       Int16 roundtrip max diff: {roundtrip_diff:.8f}")

    # ========== Summary ==========
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    print(f"Source: {AUDIO_PATH}")
    print(f"Native SR: {sr_native} Hz  |  Duration: {report['native']['duration_s']}s")
    print(f"Max amplitude: {report['native']['max_amplitude']}")
    print(f"Overall RMS: {report['native']['rms']}")
    print(f"Speech seconds: {speech_seconds}  |  Silence seconds: {silence_seconds}")
    print(f"Spectral centroid: {report['spectral']['centroid_mean_hz']} Hz")
    print(f"Segments created: {len(segments)}")
    print()

    # Energy timeline
    print("ENERGY TIMELINE (per second):")
    print(f"{'Time':>6s} | {'RMS':>10s} | {'dB':>8s} | Speech?")
    print("-" * 45)
    for v in vad_results:
        marker = "█" if v["is_speech"] else "·"
        bar_len = int(v["rms"] / max(rms_values) * 30) if max(rms_values) > 0 else 0
        print(f"{v['time_s']:5.1f}s | {v['rms']:10.6f} | {v['db']:7.2f} | {marker} {'▓' * bar_len}")

    print()
    print("SEGMENTS:")
    for s in segments:
        print(f"  [{s['index']:02d}] {s['filename']}  "
              f"({s['start_s']:.1f}-{s['end_s']:.1f}s, rms={s['rms']:.6f}, db={s['db']:.2f})")

    # Save report
    with open(ANALYSIS_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved: {ANALYSIS_OUT}")


if __name__ == "__main__":
    analyze()
