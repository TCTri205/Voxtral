# Kế hoạch triển khai: Hoàn thiện Voxtral ASR Baseline với Ngrok

## Mô tả mục tiêu

Mục tiêu là hoàn thiện pipeline baseline Voxtral ASR, hỗ trợ chạy server trên Google Colab và truy cập từ máy local thông qua **ngrok**. Đảm bảo tính khả dụng thực tế, khả năng đo lường hiệu suất (RTF) và kiểm chứng khả năng chống ảo giác.

## Các thay đổi đề xuất

### 1. Cải thiện script Client và Tiện ích

#### [MODIFY] [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py)

- Thêm hỗ trợ xử lý hàng loạt (batch processing) cho thư mục audio.
- Tính toán và ghi lại **RTF (Real Time Factor)**.
- Đảm bảo tham số `--host` hoạt động tốt với URL ngrok (ví dụ: `xxxx-xx-xx.ngrok-free.app`).
- Lưu kết quả vào `results.json`.

#### [MỚI] [generate_test_samples.py](file:///d:/VJ/Voxtral/generate_test_samples.py)

- Script tạo các file âm thanh kiểm thử: `silence_10s.wav` và `white_noise_5s.wav`.

### 2. Hoàn thiện Notebook cho Google Colab

#### [MODIFY] [voxtral_baseline.ipynb](file:///d:/VJ/Voxtral/voxtral_baseline.ipynb)

- **Tích hợp Ngrok**: Thêm cell cài đặt `pyngrok` và cấu hình tunnel để expose port 8000.
- Cải thiện cell khởi chạy vLLM để không chặn việc thực thi các cell tiếp theo (chạy background).

### 3. Cập nhật Tài liệu

#### [MODIFY] [voxtral_hallucination_analysis.md](file:///d:/VJ/Voxtral/docs/voxtral_hallucination_analysis.md)

- Thêm cấu trúc cho kết quả thực nghiệm.

#### [MODIFY] [README_SETUP.md](file:///d:/VJ/Voxtral/README_SETUP.md)

- Bổ sung hướng dẫn chi tiết về cách lấy **Ngrok Authtoken** và cấu hình kết nối Local-to-Colab.

## Kế hoạch kiểm chứng

### Kiểm tra tự động

- Chạy `run_asr.py` với host giả định để kiểm tra logic batch và RTF computation.

### Kiểm tra thủ công

1. Chạy `generate_test_samples.py` tại máy local.
2. Chạy notebook trên Google Colab, bật tunnel ngrok.
3. Chạy `run_asr.py` từ máy local trỏ đến URL ngrok.
4. Xác nhận nhận được transcript và RTF được tính toán đúng.
