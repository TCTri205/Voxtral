# Voxtral ASR Benchmark & Evaluation Suite

Chào mừng bạn đến với bộ công cụ đánh giá và so sánh hiệu năng các engine ASR (Automatic Speech Recognition). Dự án này cung cấp các công cụ để đo lường độ chính xác (CER), tốc độ (RTF), và độ ổn định (hallucination) của các hệ thống nhận dạng giọng nói.

## 🚀 Tính năng chính

- **Hỗ trợ đa Engine**: Tích hợp sẵn cho Voxtral ASR (Baseline) và Javis ASR.
- **Metrics toàn diện**:
  - **CER** (Character Error Rate): Đo độ chính xác so với Ground Truth.
  - **RTF** (Real-time Factor): Đo tốc độ xử lý (Total RTF và Inference RTF).
  - **HRS** (Hallucination Rate on Silence): Đo tỷ lệ ảo giác trên các đoạn im lặng.
- **LLM-based Evaluation**: Sử dụng LLM (OpenAI/Mistral/Groq) để phân tích lỗi ngữ nghĩa chuyên sâu.
- **Automated Benchmarking**: Chạy batch và tổng hợp kết quả tự động để đo độ ổn định.

## 📂 Cấu trúc Repository

```text
.
├── audio/                  # Dữ liệu âm thanh mẫu để benchmark
├── benchmarks/             # Kết quả benchmark tổng hợp (JSON)
├── docs/                   # Tài liệu chi tiết
├── llm_evaluator/          # Module đánh giá bằng LLM
├── reports/                # Báo cáo kết quả chi tiết (Markdown)
├── results/                # Kết quả ASR thô của Voxtral
├── results_javis/          # Kết quả ASR thô của Javis
├── run_asr.py              # Client chính cho Voxtral ASR
├── run_asr_javis.py        # Client chính cho Javis ASR
├── evaluate_metrics.py     # Công cụ tính toán CER/HRS
└── benchmark_runner.py     # Script điều phối chạy benchmark tự động
```

## 🛠️ Cài đặt nhanh

### 1. Yêu cầu hệ thống

- Python 3.9+
- Thư viện âm thanh hệ thống (ví dụ: `ffmpeg` hoặc `libsndfile`)

### 2. Thiết lập môi trường

```bash
# Tạo và kích hoạt môi trường ảo
python -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 3. Cấu hình (.env)

Copy file mẫu và điền các API Key cần thiết:

```bash
cp .env.example .env
```

*Lưu ý: Bạn cần cấu hình `VOXTRAL_HOST` cho Voxtral hoặc `JAVIS_EMAIL/PASSWORD` cho Javis.*

## ⚡ Sử dụng cơ bản

### Chạy Voxtral ASR

```bash
python run_asr.py --audio audio/sample.wav
```

### Chạy Javis ASR

```bash
python run_asr_javis.py --audio audio/sample.wav
```

### Chạy Đánh giá Metrics (CER/HRS)

```bash
python evaluate_metrics.py results/latest/results.json --gt ground_truth.json
```

## 📖 Tài liệu hướng dẫn chi tiết

Để biết thêm chi tiết về cách thiết lập server, tham số CLI và quy trình benchmark nâng cao, vui lòng tham khảo:

- [**Hướng dẫn Thiết lập và Sử dụng Voxtral ASR**](README_VOXTRAL.md)
- [**Hướng dẫn Sử dụng Javis ASR**](README_JAVIS.md)

---
*Dự án được duy trì bởi Voxtral Audit Team.*
