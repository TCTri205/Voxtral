# Báo cáo Tổng kết Công việc ngày 21/05/2026 - VAD Chunk V9

## 1. Tổng quan mục tiêu
Tập trung cải thiện độ ổn định của hệ thống ASR Voxtral, triệt tiêu lỗi mất chữ đầu câu (Deletion) và xử lý các ảo giác (Hallucination) phát sinh từ nhiễu nền hoặc lỗi biên nối chunk.

## 2. Các cải tiến kỹ thuật chính

- **Chống mất chữ đầu câu (Speech Onset Truncation):** Nâng VAD Padding đầu lên **300ms**, giúp khắc phục triệt để lỗi bị cắt âm thanh khi bắt đầu nói (Tỷ lệ lỗi Deletion giảm xuống 0).
- **Triệt tiêu ảo giác tiếng ồn trầm (Hum/Rumble):** Áp dụng bộ lọc **High-Pass Filter (80Hz)**, loại bỏ nhiễu tần số thấp và ngăn chặn ảo giác sinh ra từ tiếng ù nền (HRS duy trì mức 0.0).
- **Tinh chỉnh phần merge chunk:** Nâng cấp **Fuzzy Overlap Matching** với logic "monotonic boundary-matching chain", siết chặt khoảng cách biên (15 -> 6 ký tự) giúp xử lý mượt mà các đoạn nối bị nhiễu.
- **Mở rộng Guardrails bảo vệ:** Nâng phạm vi n-gram lên đến **12** để phát hiện các ảo giác lặp câu dài và siết chặt cơ chế **Strict Rollback** (chỉ chấp nhận kết quả retry nếu thực sự sạch lỗi hơn bản gốc).
- **Tối ưu hóa GPU T4:** Tắt 4-bit quantization để đảm bảo độ chính xác cao nhất trên phần cứng hiện có.

## 3. Kết quả Benchmark (Run v6 - Final Stable)

Kết quả đo đạc trên 9 file speech chính (không tính file im lặng):

| Chỉ số | Giá trị | Đánh giá |
|---|---|---|
| **CER (Speech Only)** | **34.54%** | Cải thiện nhẹ so với V8 (35.27%) |
| **Inference RTF (Avg)** | **1.354** | Cao hơn mức 1.0 (cần tối ưu thêm) |
| **HRS (Silence)** | **0.00** | Hoàn hảo |
| **Lỗi Deletion** | **0** | Đã khắc phục hoàn toàn |

### 3.1. Chi tiết kết quả từng file (Run v6)

| File | CER | RTF Inf | Trạng thái |
|---|---|---|---|
| `media_148280` | 44.02% | 1.272 | Success |
| `media_148284` | 28.46% | 1.025 | Success |
| `media_148393` | 35.11% | 1.404 | Success |
| `media_148394` | 35.18% | 1.630 | Success |
| `media_148414` | 34.95% | 1.244 | Success |
| `media_148439` | 22.60% | 1.489 | Success |
| `media_148954` | 29.14% | 1.639 | Success |
| `media_149291` | 30.19% | 1.396 | Success |
| `media_149733` | 51.23% | 1.085 | Success |
| **Trung bình (9 file Speech)** | **34.54%** | **1.354** | |

## 4. Phân tích & Hướng phát triển (V10)

- **Nguyên nhân CER còn cao:** Phần lớn là lỗi **Substitution** (nghe sai âm vị danh từ riêng) do giới hạn của acoustic model, không phải lỗi pipeline.
- **Vấn đề Local Language Collapse:** Phát hiện mô hình đôi khi sinh ra tiếng Anh/Tây Ban Nha ngắn ở cuối chunk.
- **Kế hoạch V10:** Triển khai Regex phát hiện chuỗi Latin liên tục (12+ ký tự) và thử nghiệm giảm VAD Padding (300ms -> 200ms) để đưa RTF về sát mức 1.0.

---
**Người tổng hợp:** Gemini CLI Agent
**Trạng thái mã nguồn:** Đã ổn định tại commit `2e3e402`
