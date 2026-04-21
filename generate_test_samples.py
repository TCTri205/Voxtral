import numpy as np
import scipy.io.wavfile as wav
import os

def generate_silence(duration_sec, sample_rate=16000, filename="silence.wav", noise_floor_db=-50):
    """
    Tạo file âm thanh im lặng nhưng có một chút nhiễu nền dither (noise floor).
    Điều này thực tế hơn là im lặng tuyệt đối (np.zeros).
    """
    # Tính toán biên độ dựa trên dB (0dB = 32767)
    amplitude = 10 ** (noise_floor_db / 20)
    samples = np.random.uniform(-amplitude, amplitude, int(duration_sec * sample_rate))
    
    # Convert to int16
    samples = (samples * 32767).astype(np.int16)
    wav.write(filename, sample_rate, samples)
    print(f"Created {filename} ({duration_sec}s, noise floor: {noise_floor_db}dB)")

def generate_white_noise(duration_sec, sample_rate=16000, filename="white_noise.wav", amplitude_db=-6):
    """
    Tạo file âm thanh nhiễu trắng mạnh.
    -6dB là biên độ lớn (khoảng 50% scale), đủ để stress test cực mạnh.
    """
    amplitude = 10 ** (amplitude_db / 20)
    samples = np.random.uniform(-amplitude, amplitude, int(duration_sec * sample_rate))
    
    # Convert to int16
    samples = (samples * 32767).astype(np.int16)
    wav.write(filename, sample_rate, samples)
    print(f"Created {filename} ({duration_sec}s, amplitude: {amplitude_db}dB)")

def generate_unstable_noise(duration_sec, sample_rate=16000, filename="stochastic_noise.wav", base_amplitude_db=-12):
    """
    Tạo nhiễu 'phi quy luật' (Truly Random/Stochastic):
    - Không dùng Sine (tránh lặp lại tuần hoàn).
    - Sử dụng Random Walk/Smoothed Noise cho Volume Envelope.
    - Thêm các đoạn Burst và Dropout ngẫu nhiên.
    """
    n_samples = int(duration_sec * sample_rate)
    samples = np.random.uniform(-1, 1, n_samples)
    
    # 1. Non-periodic Volume Envelope (Smoothed Random Walk)
    low_res_n = int(duration_sec * 5) # 5 điểm kiểm soát mỗi giây
    envelope_points = np.random.uniform(0.1, 1.0, low_res_n)
    
    # Interpolate để làm mượt envelope (tránh click/pop khi đổi volume)
    envelope = np.interp(
        np.linspace(0, duration_sec, n_samples),
        np.linspace(0, duration_sec, low_res_n),
        envelope_points
    )
    
    samples *= envelope
    
    # 2. Chaotic Bursts (Xung nhiễu mạnh đột ngột)
    n_bursts = int(duration_sec / 2)
    for _ in range(n_bursts):
        burst_len = int(np.random.uniform(0.05, 0.4) * sample_rate)
        start = np.random.randint(0, n_samples - burst_len)
        burst_amp = np.random.uniform(0.4, 0.9)
        samples[start:start+burst_len] += np.random.uniform(-burst_amp, burst_amp, burst_len)
        
    # 3. Random Dropouts (Khoảng lặng đột ngột)
    n_dropouts = int(duration_sec / 10)
    for _ in range(n_dropouts):
        drop_len = int(np.random.uniform(0.2, 0.8) * sample_rate)
        start = np.random.randint(0, n_samples - drop_len)
        samples[start:start+drop_len] *= 0.05 # Gần như im lặng
    
    # Protection
    samples = np.clip(samples, -1.0, 1.0)
    
    # Scale to base amplitude
    amplitude = 10 ** (base_amplitude_db / 20)
    samples = (samples * amplitude * 32767).astype(np.int16)
    
    wav.write(filename, sample_rate, samples)
    print(f"Created {filename} ({duration_sec}s, chaos/stochastic)")

if __name__ == "__main__":
    output_dir = "audio"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 1. 60s Im lặng (Dithered) - Cần 60s để đo HRS < 0.5 CPM chính xác
    generate_silence(60, filename=os.path.join(output_dir, "silence_60s.wav"), noise_floor_db=-50)
    
    # 2. 60s Nhiễu 'Phi quy luật' (Realistic stress test)
    # 60s giúp quan sát sự ổn định dài hạn của Decoder
    generate_unstable_noise(60, filename=os.path.join(output_dir, "stochastic_noise_60s.wav"), base_amplitude_db=-12)
    
    # 3. 60s White Noise (Baseline)
    generate_white_noise(60, filename=os.path.join(output_dir, "white_noise_60s.wav"), amplitude_db=-6)
    
    print("\nProduction-grade stress test samples (60s) generated in 'audio/' directory.")
