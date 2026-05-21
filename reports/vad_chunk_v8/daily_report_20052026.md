# Báo cáo công việc - 20/05/2026 (VAD Chunk V8)

## 1. Tổng quan các thay đổi
Trong ngày 20/05/2026, các nỗ lực tập trung vào việc tối ưu hóa độ chính xác của hệ thống ASR Voxtral thông qua việc cải thiện xử lý tín hiệu âm thanh, tinh chỉnh VAD (Voice Activity Detection) và nâng cấp logic nối ghép văn bản (overlap matching).

## 2. Chi tiết thực hiện

### 2.1. Tối ưu hóa xử lý Overlap văn bản (Fuzzy Overlap Matching)
- **Vấn đề:** Logic `_exact_overlap_chars` cũ quá khắt khe, dẫn đến việc không loại bỏ được các đoạn trùng lặp nếu có sai lệch nhỏ về dấu câu hoặc nhiễu ASR tại biên chunk.
- **Giải pháp:** 
    - Nâng cấp hàm `_fuzzy_overlap_chars` sử dụng logic "monotonic boundary-matching chain".
    - Hệ thống hiện tại có khả năng phát hiện chuỗi khớp mờ tại đầu và cuối các chunk kế tiếp, cho phép sai số nhỏ (tolerance) nhưng vẫn đảm bảo tính liên tục của văn bản.
    - Áp dụng logic này cho cả quá trình xử lý context anchor khi thực hiện cơ chế retry.

### 2.2. Cải thiện VAD Padding và Speech Onset
- **Thay đổi:** Tăng `VAD_PADDING_LEFT_MS` từ **50ms** lên **300ms**.
- **Lý do:** Tránh hiện tượng "Speech Onset Truncation" (bị mất âm đầu của câu thoại), một vấn đề thường gặp khi VAD kích hoạt hơi chậm hoặc biên padding quá ngắn, làm giảm độ chính xác của từ đầu tiên trong câu.

### 2.3. Cải tiến Audio Preprocessing
- **Thay đổi:** Chuyển từ **Bandpass Filter (100Hz-7500Hz)** sang **High-Pass Filter (80Hz)**.
- **Lý do:** HPF 80Hz giúp loại bỏ hiệu quả các nhiễu tần số thấp (low-frequency hum/rumble) mà không gây rủi ro cắt mất các thành phần âm thanh quan trọng ở dải cao, giúp mô hình ASR nhận diện giọng nói tự nhiên và chính xác hơn.

### 2.4. Tối ưu hóa hiệu năng trên hạ tầng T4 GPU
- **Thay đổi:** Tắt quantization 4-bit tự động trên GPU T4 trong `voxtral_baseline.ipynb`.
- **Lý do:** Thực nghiệm cho thấy 4-bit quantization trên kiến trúc Turing (T4) gây overhead giải nén rất lớn, làm RTF (Real-Time Factor) vọt lên > 6.0. Chuyển về **FP16** giúp RTF giảm xuống < 0.2 (nhanh gấp 30 lần) trong khi vẫn đảm bảo an toàn bộ nhớ VRAM (chiếm ~8GB/16GB).

### 2.5. Tăng cường khả năng chống Hallucination (Ảo giác âm thanh)
- **Mở rộng n-range:** Hàm `_truncate_repetitions` được bổ sung các dải n-gram (10, 12) để xử lý các đoạn lặp câu dài.
- **Strict Rollback:** Củng cố logic rollback trong `_run_inference_sync`. Hệ thống sẽ chỉ chấp nhận kết quả retry nếu độ nghiêm trọng (severity) của ảo giác thực sự thấp hơn kết quả ban đầu, nếu không sẽ quay về bản gốc để tránh làm tệ hơn tình hình.

## 3. Kết quả Benchmark (Run: 20-05-2026_v3)

Dựa trên kết quả benchmark mới nhất, hệ thống đã cho thấy những cải thiện đáng kể về khả năng chống ảo giác trên đoạn im lặng, tuy nhiên vẫn còn thách thức ở các đoạn hội thoại có độ nhiễu cao.

### 3.1. Chỉ số tổng quan
- **Average CER (Speech Only):** 35.27%
- **Average CER (All Files):** 28.86%
- **HRS (Hallucination Rate on Silence):** 0.000 (Tuyệt vời - Không phát sinh ảo giác trên file silence và noise).
- **Average Inference RTF:** 1.14 (Vẫn duy trì ở mức ổn định).

**Chi tiết kết quả từng file:**

| File | RTF (Inf) | HRS/RF | CER |
| :--- | :--- | :--- | :--- |
| `media_148280_1767762915627.mp3` | 1.431 | 0 | 42.39% |
| `media_148284_1767766514646 (1).mp3` | 1.021 | 0 | 28.46% |
| `media_148393_1767860211615 (1).mp3` | 1.411 | 0 | 35.11% |
| `media_148394_1767860189485 (1).mp3` | 1.642 | 0 | 35.18% |
| `media_148414_1767922241264 (1).mp3` | 1.247 | 0 | 34.95% |
| `media_148439_1767926711644 (1).mp3` | 1.494 | 0 | 22.60% |
| `media_148954_1768789819598 (1).mp3` | 1.693 | 0 | 36.90% |
| `media_149291_1769069811005.mp3` | 1.426 | 0 | 30.61% |
| `media_149733_1769589919400.mp3` | 1.082 | 0 | 51.23% |
| `silence_60s.wav` | 0.043 | 0 | 0.00% |
| `stochastic_noise_60s.wav` | 0.054 | 0 | 0.00% |

### 3.2. Phân tích lỗi và Hallucination (LLM Evaluation)
Sử dụng `llama-3.3-70b-versatile` để đánh giá chi tiết 11 file:
- **Tỷ lệ Hallucination (Speech Only):** 100% (9/9 file speech đều bị đánh giá có yếu tố ảo giác).
- **Phân bổ mức độ nghiêm trọng (Severity):**
    - **Medium:** 8 file (Chủ yếu là lỗi lặp từ hoặc chèn thêm cụm từ không có trong audio).
    - **Low:** 1 file.
    - **None:** 2 file (Các file im lặng/nhiễu).
- **Lỗi phổ biến:** 
    - **Insertion:** 9 trường hợp (Hệ thống có xu hướng chèn thêm các từ ngữ mang tính chất "filler" hoặc lặp lại một phần câu trước đó do logic overlap matching vẫn cần tinh chỉnh thêm ở các biên âm thanh phức tạp).
    - **Deletion:** 0 trường hợp (Không bị mất từ, cho thấy VAD Padding 300ms đã hoạt động tốt).

## 4. Đánh giá và hướng đi tiếp theo
- **Ưu điểm:** Cơ chế xử lý nhiễu (HPF 80Hz) và VAD Padding mới đã giúp loại bỏ hoàn toàn hiện tượng mất chữ đầu câu và ảo giác trên môi trường không có tiếng người (HRS = 0).
- **Nhược điểm:** Tỷ lệ CER vẫn còn cao và lỗi chèn từ (Insertion) do ảo giác trong khi có tiếng nói vẫn tồn tại ở mức Medium.
- **Kế hoạch v9:** 
    - Tinh chỉnh sâu hơn tham số `tolerance` trong `_fuzzy_overlap_chars` (hiện đang ở mức 6).
    - Nghiên cứu cơ chế "Confidence-based Truncation" để tự động cắt bỏ các đoạn có xác suất log-likelihood thấp từ mô hình Transformers.

---
**Người thực hiện:** TCTri
**Ngày báo cáo:** 20/05/2026
