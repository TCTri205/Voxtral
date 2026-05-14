# Báo Cáo Tổng Hợp Công Việc - Dự Án Voxtral ASR (14/05/2026)

## 1. Tổng Quan Công Việc
Ngày làm việc 14/05/2026 tập trung vào việc gia cố hạ tầng WebSocket, triển khai các lớp tiền xử lý âm thanh (Audio Preprocessing) và thiết lập các "Guardrails" thông minh để ngăn chặn ảo giác (Hallucination). 

Mặc dù đã triển khai nhiều tính năng mới, kết quả Benchmark **v9** cho thấy sự sụt giảm về hiệu suất (RTF) và độ chính xác (CER) do các vấn đề phát sinh từ việc chia nhỏ đoạn hội thoại (Over-segmentation) và lỗi sập ngôn ngữ mới (Russian language collapse).

---

## 2. Nhật Ký Triển Khai Chi Tiết (Step-by-Step)

### Bước 1: Ổn định hạ tầng truyền tải (WebSocket Resilience)
- **Hành động:** Nâng cấp cơ chế gửi tin nhắn an toàn (`safe_send`), tự động hủy task khi ngắt kết nối và cập nhật báo cáo tiến độ (Commit `05b3538`).
- **Nguyên nhân:** Khắc phục tình trạng treo server hoặc rò rỉ bộ nhớ khi client ngắt kết nối đột ngột trong lúc inference.
- **Kết quả:** WebSocket hoạt động ổn định 100% trong suốt quá trình chạy Batch Test v9.

### Bước 2: Tiền xử lý âm thanh chuyên sâu (Audio Preprocessing)
- **Hành động:** Triển khai bộ lọc DC offset removal, Peak Normalization và High-Pass Filter (HPF) (Commit `a9c19b4`, `1478577`).
- **Nguyên nhân:** Loại bỏ nhiễu tần số thấp và chuẩn hóa biên độ tín hiệu trước khi đưa vào VAD/ASR để cải thiện độ nhạy.
- **Kết quả:** Hệ thống đạt tỷ lệ nhận diện nhiễu trắng/im lặng chính xác tuyệt đối (0% CER trên file nhiễu).

### Bước 3: Triển khai Guardrails chống ảo giác (V5 Optimization)
- **Hành động:** Tích hợp RMS Normalization, n-gram looping detection (phát hiện lặp từ n=4) và cơ chế Multi-temperature Retry (Commit `faa314f`, `b063cef`).
- **Nguyên nhân:** Ngăn chặn các vòng lặp vô tận của mô hình khi gặp audio chất lượng thấp hoặc giọng địa phương khó nghe.
- **Kết quả:** Đã có cơ chế tự động ngắt sớm các đoạn transcript bị lỗi lặp, tránh lãng phí tài nguyên GPU.

### Bước 4: Tối ưu hóa cho phiên làm việc dài (Long Sessions)
- **Hành động:** Tăng ngưỡng `keepalive_threshold` từ 85 lên **250** (Commit `05c4226`).
- **Nguyên nhân:** Các file audio dài (>2 phút) thường bị ngắt kết nối sớm do thời gian inference vượt quá giới hạn timeout cũ.
- **Kết quả:** Đảm bảo xử lý trọn vẹn các file lớn như `media_149291` (156 giây).

### Bước 5: Khắc phục lỗi Regression & Tinh chỉnh (Hotfixes)
- **Hành động:** Revert tính năng `ENABLE_RETRY_HALLUCINATION` (gây chậm RTF 4 lần) và sửa lỗi nhận diện nhầm n-gram loop cho tiếng Nhật (Commit `ce2cb5a`, `e03f8c6`, `1478577`).
- **Nguyên nhân:** Phát hiện RTF vọt lên >8.0 do cơ chế retry quá đà và stopping criteria chưa tối ưu cho cấu trúc ngữ pháp Nhật Bản.
- **Kết quả:** RTF ổn định trở lại ở mức chấp nhận được, mặc dù vẫn cao hơn mục tiêu đề ra.

---

## 3. Kết Quả Benchmark (So sánh v9 ngày 14/05 với v6 ngày 12/05)

| Chỉ số | v9 (14/05) | v6 (12/05) | Chênh lệch | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Average CER** | **43.28%** | **44.53%** | 📉 **Giảm 1.25%** | **Cải thiện nhẹ** |
| **Average RTF** | **3.57** | **2.10** | 📈 **Tăng 1.47** | **Chậm hơn** |
| **Language Collapse** | **Bị tiếng Nga** | **Không bị** | ⚠️ Lỗi logic mới | Nghiêm trọng |
| **Noise Resilience** | **100%** | **~95%** | ✅ Tăng 5% | Rất tốt |

---

## 4. Các Vấn Đề Tồn Đọng & Khó Khăn
- **Ảo giác Nga (Russian Hallucinations):** Logic phát hiện sập ngôn ngữ hiện tại chỉ lọc ASCII (tiếng Anh), không chặn được tiếng Nga/Cyrillic.
- **Over-segmentation:** Tham số `VAD_SEGMENT_SILENCE_MS = 700ms` đang quá ngắn, làm nát câu và mất ngữ cảnh, dẫn đến sai lệch thông tin thực thể (số điện thoại, tên riêng).
- **Inference Stalling:** Một số đoạn audio khó khiến model chạy hết `max_new_tokens`, đẩy RTF lên mức cực cao (>9.0).

---

## 5. Kế Hoạch Tiếp Theo (Next Steps)
1. **Nâng cấp Guardrail Ngôn ngữ:** Thay đổi logic kiểm tra `Japanese Character Ratio` thay vì chỉ dùng ASCII ratio.
2. **Gộp câu VAD:** Tăng `VAD_SEGMENT_SILENCE_MS` lên **1000ms - 1200ms** để duy trì ngữ cảnh.
3. **Band-pass Filter:** Áp dụng bộ lọc 300Hz-3.4kHz để xử lý đặc thù nhiễu điện thoại (Telephony).
4. **Time-based Guardrail:** Thêm `max_time_per_chunk` để ngắt ngay các inference bị đình trệ quá lâu.

---
**Người thực hiện báo cáo:** Antigravity AI  
**Ngày cập nhật:** 14/05/2026 (17:00 UTC+7)  
**Phiên bản hệ thống cuối:** 2026-05-14.4 (v7 core)
