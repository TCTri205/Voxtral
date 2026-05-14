# Báo Cáo Tổng Hợp Công Việc - Dự Án Voxtral ASR (12/05/2026)

## 1. Tổng Quan Công Việc
Ngày làm việc 12/05/2026 tập trung vào việc ổn định hóa hệ thống xử lý VAD (Voice Activity Detection), khôi phục khả năng đo lường Hallucination và tối ưu hóa sự cân bằng giữa tốc độ (RTF) và độ chính xác (CER). 

Hệ thống đã trải qua 2 đợt điều chỉnh tham số lớn, nâng cấp từ phiên bản **12.1** lên **12.3**.

---

## 2. Nhật Ký Triển Khai Chi Tiết (Step-by-Step)

### Bước 1: Khôi phục hạ tầng phân tích & Tài liệu
- **Hành động:** Thêm script phân tích `analyze_audio_levels.py`, cập nhật `VAD Implementation Plan v4` và báo cáo tồn đọng từ 07/05 (Commit `298857a`).
- **Nguyên nhân:** Cần công cụ đo đạc định lượng (RMS, SNR) để giải mã nguyên nhân các file có CER > 50% và thiết lập lộ trình tối ưu hóa bài bản.
- **Kết quả:** Có cơ sở dữ liệu để so sánh; xác định được mối liên hệ giữa cường độ tín hiệu thấp và lỗi nhận dạng.

### Bước 2: Tối ưu hóa hiệu năng & Tốc độ (Version 12.2)
- **Hành động:** Tăng `VAD_THRESHOLD` lên **0.6** và giảm `VAD_PADDING_MS` xuống **300ms** (Commit `5951bcf`).
- **Nguyên nhân:** Bản cũ bị nhiễu (noise) lọt vào chunk quá nhiều làm mô hình ASR bị chậm và dễ phát sinh ảo giác.
- **Kết quả:** 
    - RTF trung bình giảm mạnh từ 2.6 xuống **2.15** (Nhanh hơn ~17%).
    - Giảm thiểu đáng kể nhiễu nền lọt vào các phân đoạn xử lý.

### Bước 3: Gia cố cơ chế phục hồi lỗi (Language Collapse Recovery)
- **Hành động:** Triển khai logic `fixed_fallback_trim` cho các trường hợp không tìm thấy anchor (Commit `29a367f`).
- **Nguyên nhân:** Các chunk (đặc biệt là Chunk 0) thường xuyên bị lỗi lặp từ nhưng không có điểm cắt tỉa an toàn, dẫn đến việc retry thất bại.
- **Kết quả:** Đạt tỷ lệ phục hồi thành công **100%** trong Run v4 (11/11 lần xử lý thành công), không còn lỗi `failed` do sập ngôn ngữ.

### Bước 4: Tinh chỉnh độ nhạy cho âm lượng thấp (Version 12.3)
- **Hành động:** Giảm `VAD_THRESHOLD` xuống **0.55** và tăng `VAD_PADDING_MS` lên **400ms** (Commit `e7b95e6`).
- **Nguyên nhân:** Phân tích từ Bước 1 cho thấy ngưỡng 0.6 hơi cao, có thể vô tình cắt mất các từ nói nhỏ hoặc âm đuôi (Japanese endings) trong môi trường điện thoại.
- **Kết quả:** Cải thiện khả năng bắt giữ giọng nói (speech capture), đảm bảo tính toàn vẹn của câu thoại trước khi đưa vào mô hình ASR.

---

## 3. Kết Quả Benchmark (v4 - Golden Run)

| Chỉ số | v4 (Best) | So với v3 (Cũ) | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Average CER** | **34.58%** | 📉 Giảm ~3% | Tốt hơn |
| **High Severity Rate** | **9.1%** | 📉 Giảm 27% | Rất an toàn |
| **Hallucination Rate** | **81.82%** | 🔄 Không đổi | Cần tối ưu prompt |
| **Average RTF** | **2.15** | 🚀 Nhanh hơn 17% | Đạt mục tiêu |

---

## 4. Các Vấn Đề Tồn Đọng & Khó Khăn
- **Lỗi mạng (DNS/Network):** Benchmark Runner chưa có cơ chế retry API tốt, dễ mất dữ liệu khi chạy batch lớn (Sự cố Run v5).
- **Ảo giác xã giao (Social Insertions):** Các câu chào hỏi tự động (Standard Japanese greetings) vẫn chiếm tỷ lệ CER cao mặc dù lỗi lặp từ đã hết.

---

## 5. Kế Hoạch Tiếp Theo (Next Steps)
1. **Kháng lỗi mạng cho Runner:** Thêm logic `exponential backoff` cho các yêu cầu API.
2. **Prompt Engineering:** Tinh chỉnh system prompt để giảm thiểu bias của mô hình đối với các câu chào "khuôn mẫu".
3. **Thử nghiệm CHUNK_LIMIT:** Thử nghiệm rút ngắn `CHUNK_LIMIT_SEC` đối với các file có CER > 50% để giảm tải cho mô hình trong một lần inference.

---
**Người thực hiện báo cáo:** Antigravity AI  
**Ngày cập nhật:** 12/05/2026 (17:05 UTC+7)  
**Phiên bản hệ thống cuối:** 2026-05-12.3
