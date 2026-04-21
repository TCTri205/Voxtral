# Hướng dẫn Thiết lập và Sử dụng Javis ASR Engine

Tài liệu này hướng dẫn cách cấu hình và chạy benchmark cho Javis ASR engine trong pipeline của Voxtral.

## 1. Thành phần Hệ thống

- **ASR Engine**: Javis (truy cập qua WebSocket API).
- **Client (`run_asr_javis.py`)**: Kết nối tới Javis, stream audio và lấy transcript.
- **Authentication (`javis_auth.py`)**: Tự động hóa đăng nhập và quản lý token.
- **Orchestrator (`benchmark_runner.py`)**: Chạy batch nhiều lần để đo độ ổn định.

---

## 2. Cấu hình Môi trường (.env)

Yêu cầu cấu hình các tham số Javis trong file `.env`. Bạn có thể sử dụng Email/Password (khuyên dùng) hoặc Token thủ công.

| Biến | Ví dụ | Ý nghĩa |
| :--- | :--- | :--- |
| `JAVIS_EMAIL` | `user@example.com` | Email tài khoản Javis. |
| `JAVIS_PASSWORD` | `********` | Mật khẩu tài khoản Javis. |
| `JAVIS_WS_URL` | `wss://api2.../ws/improved` | URL WebSocket của Javis Engine. |
| `JAVIS_SESSION_ID` | `(tùy chọn)` | Ghi đè Session ID thủ công. |
| `JAVIS_TOKEN` | `(tùy chọn)` | Ghi đè Access Token thủ công. |

> [!TIP]
> Nếu bạn điền `JAVIS_EMAIL` và `JAVIS_PASSWORD`, hệ thống sẽ tự động đăng nhập để lấy token mới mỗi khi chạy, giúp tránh lỗi hết hạn token.

---

## 3. Hướng dẫn Sử dụng Client (`run_asr_javis.py`)

### Danh sách tham số (CLI Flags)

| Cờ | Ý nghĩa |
| :--- | :--- |
| `--audio [file]` | Xử lý một file audio duy nhất. |
| `--audio_dir [dir]` | Xử lý batch toàn bộ file trong thư mục. |
| `--ws-url [url]` | Ghi đè URL WebSocket từ `.env`. |
| `--language [code]` | Ngôn ngữ: `ja` (mặc định), `vi`, `en`, `auto`. |
| `--noise-suppression` | Bật chống nhiễu từ phía server. |
| `--denoiser [type]` | Chọn denoiser: `demucs` (mặc định), `df`, `webrtc`. |
| `--chunk-interval [s]` | Pacing: `0.1` (mô phỏng realtime), `0` (tối đa tốc độ). |
| `--llm-eval` | Chạy đánh giá hallucination bằng LLM sau khi ASR xong. |
| `--llm-model [name]` | Chọn model LLM (mặc định: `llama-3.3-70b-versatile`). |
| `--debug` | Hiển thị log chi tiết về quá trình xác thực và handshake. |

> [!NOTE]
> Client đã được cấu trúc lại theo mô hình **Asynchronous (Bất đồng bộ)**. Việc gửi audio và nhận kết quả diễn ra song song, giúp duy trì kết nối WebSocket ổn định ngay cả khi stream realtime (`--chunk-interval 0.1`).

### Ví dụ chạy lệnh

#### 1. Chạy thử một file (Realtime mode)

```bash
python run_asr_javis.py --audio audio/test.wav --chunk-interval 0.1 --debug
```

#### 2. Chạy batch toàn bộ thư mục

```bash
python run_asr_javis.py --audio_dir audio --chunk-interval 0
```

---

## 4. Chạy Benchmark tự động (`benchmark_runner.py`)

Để so sánh Javis với các engine khác hoặc đo độ ổn định, sử dụng `--engine javis`:

```bash
# Chạy 3 lần batch để lấy kết quả trung bình
python benchmark_runner.py --engine javis --audio_dir audio --runs 3
```

---

## 5. Quy trình Tối ưu (Tách biệt ASR và Evaluation)

Để tối ưu tài nguyên (tiết kiệm thời gian và API credit), bạn có thể chia quy trình làm 2 giai đoạn:

### Giai đoạn 1: Chạy ASR thực tế

Chạy ASR để thu thập transcript và các chỉ số RTF/Latency:

```bash
python benchmark_runner.py --engine javis --audio_dir audio --runs 3
```

### Giai đoạn 2: Đánh giá Hallucination (Standalone)

Sau khi có kết quả trong `results_javis/`, chạy đánh giá LLM độc lập mà không cần gọi lại ASR:

```bash
# Đánh giá toàn bộ kết quả của một ngày
python benchmark_runner.py --engine javis --eval-only --date 19-04-2026 --llm-eval

# Đánh giá theo khoảng version (ví dụ từ v1 đến v5)
python benchmark_runner.py --engine javis --eval-only --date 19-04-2026 --start-v 1 --end-v 5 --llm-eval
```

Hoặc chạy đánh giá trực tiếp trên một file `results.json`:

```bash
python -m llm_evaluator.batch_runner --results results_javis/19-04-2026_v1/results.json
```

---

## 6. Đánh giá Hallucination (LLM Evaluation)

Để chạy đánh giá độ chính xác và phát hiện hallucination bằng LLM ngay sau khi lấy transcript:

```bash
# Chạy ASR và LLM Eval cho toàn bộ thư mục
python run_asr_javis.py --audio_dir audio --llm-eval
```

Bạn cũng có thể chạy trong benchmark runner để đo độ ổn định hallucination:

```bash
python benchmark_runner.py --engine javis --audio_dir audio --runs 3 --llm-eval
```

---

## 7. Cơ chế Tự động Xác thực (Authentication)

Hệ thống sử dụng module `javis_auth.py` để quản lý quyền truy cập:

1. **Ưu tiên 1**: Sử dụng `JAVIS_SESSION_ID` và `JAVIS_TOKEN` nếu có sẵn trong `.env`.
2. **Ưu tiên 2**: Nếu thiếu, hệ thống dùng `JAVIS_EMAIL` và `JAVIS_PASSWORD` để gọi API đăng nhập của Javis, lấy token mới và sinh Session ID ngẫu nhiên.

---

## 8. Kết quả (Results)

Mặc định, các kết quả của Javis sẽ được tách biệt hoàn toàn với Voxtral:

- **Thư mục lưu trữ**: `results_javis/`
- **Kết quả tổng hợp**: `benchmarks_javis/benchmark_YYYYMMDD_HHMMSS.json`

Bạn có thể thay đổi thư mục lưu trữ Javis bằng tham số `--output_root`:

```bash
python run_asr_javis.py --audio audio/test.wav --output_root my_custom_results
```

---

## 9. Giải quyết vấn đề (Troubleshooting)

- **Lỗi `Failed to authenticate`**: Kiểm tra Email/Password trong `.env` và kết nối mạng.
- **WebSocket Timeout/Closed**: Hệ thống hiện đã tự động xử lý pongs heartbeats. Nếu vẫn gặp lỗi, hãy kiểm tra tốc độ mạng hoặc tăng `--response-timeout`.
- **Transcript rỗng**:
  - Đảm bảo `--language` khớp với audio.
  - Hệ thống đã tích hợp cơ chế **Fallback**: Nếu Javis trả về tin nhắn `final` trống, client sẽ tự động lấy kết quả từ các tin nhắn `partial` trước đó (dựa trên cấu trúc `lines` của server).

---
Tài liệu hướng dẫn Javis Integration - Cập nhật 19/04/2026
