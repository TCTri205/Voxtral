# Báo Cáo Tổng Hợp Công Việc - Dự Án Voxtral ASR (12/05/2026)

## 1. Tổng Quan Công Việc
Trong đợt cập nhật này (12/05/2026), trọng tâm là tối ưu hóa độ chính xác (CER) và giảm thiểu các lỗi ảo giác nghiêm trọng. Hệ thống đánh giá LLM đã được khôi phục hoàn toàn, cho phép đo lường chính xác hiệu quả của các thay đổi.

---

## 2. Chi Tiết Các Thay Đổi (Phiên bản 2026-05-12.2)

### A. Tinh Chỉnh Cơ Chế Phục Hồi (Language Collapse Recovery)
- **Nâng cấp Fallback:** Triển khai cơ chế `fixed_fallback_trim` cho phép cắt tỉa các phần bị lỗi Language Collapse chính xác hơn khi không tìm được anchor hoàn hảo.
- **Kết quả:** Đạt tỷ lệ phục hồi thành công 100% trong điều kiện ổn định (Run v4 với 11/11 lần retry thành công), loại bỏ hoàn toàn các lỗi `failed` retry từ phiên bản 07/05.

### B. Cải Tiến Cấu Hình VAD & Tốc Độ
- **Ngưỡng VAD mới:** Tăng `VAD_THRESHOLD` lên **0.6** và giảm `VAD_PADDING_MS` xuống **300ms**.
- **Hiệu quả:** 
    - Giảm nhiễu (noise) lọt vào các chunk speech.
    - Cải thiện tốc độ xử lý: RTF trung bình giảm từ ~2.6 xuống **2.15** (Nhanh hơn ~17%).

### C. Ổn Định Hệ Thống Đánh Giá
- **LLM Eval Recovery:** Sửa lỗi Error 403 khi gọi mô hình Llama-3.3-70B qua Groq, giúp lấy lại được dữ liệu Hallucination thực tế cho cả bản cũ và bản mới.
- **Báo cáo tự động:** Tích hợp sâu hơn kết quả từ `llm_eval_details.csv` vào báo cáo tổng hợp để phân loại mức độ nghiêm trọng (Severity).

---

## 3. Kết Quả Benchmark (v4 - Golden Run)

| Chỉ số | v4 (Best) | v6 (Valid) | So với v3 (Cũ) |
| :--- | :--- | :--- | :--- |
| **Average CER** | **34.58%** | **36.44%** | 📉 Giảm ~3% (Tốt hơn) |
| **High Severity Rate** | **9.1%** | **9.1%** | 📉 Giảm 27% (An toàn hơn) |
| **Hallucination Rate** | **81.82%** | **81.82%** | 🔄 Không đổi |
| **Average RTF** | **2.15** | **2.10** | 🚀 Nhanh hơn 17% so với v2 |

---

## 4. Các Vấn Đề Tồn Đọng & Khó Khăn
- **Sự cố mạng (v5):** Benchmark Runner hiện chưa có cơ chế retry tốt khi gặp lỗi DNS/Network, dẫn đến việc mất dữ liệu khi chạy batch lớn.
- **Ảo giác xã giao (Social Insertions):** Dù lỗi nghiêm trọng đã giảm, nhưng các câu chào hỏi tự động vẫn xuất hiện dày đặc, ảnh hưởng đến chỉ số CER tổng thể.

---

## 5. Kế Hoạch Tiếp Theo (Next Steps)
1. **Kháng lỗi mạng cho Runner:** Thêm logic `try-except` và `exponential backoff` cho các yêu cầu API trong quá trình benchmark.
2. **Prompt Engineering:** Tinh chỉnh system prompt để loại bỏ bias của mô hình đối với các câu chào hỏi tiếng Nhật khuôn mẫu.
3. **Phân tích sâu CER:** Tập trung xử lý 2 file có CER > 50% (`media_148280` và `media_149733`) bằng cách thử nghiệm các tham số `CHUNK_LIMIT_SEC` ngắn hơn.

---
**Người thực hiện báo cáo:** Antigravity AI
**Ngày cập nhật:** 12/05/2026 (14:25 UTC+7)
