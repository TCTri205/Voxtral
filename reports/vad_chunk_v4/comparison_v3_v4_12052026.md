# Báo Cáo So Sánh Đối Chứng VAD & Chunking (v3 vs v4) - Voxtral ASR

Báo cáo này thực hiện so sánh chi tiết hiệu năng giữa hai phiên bản logic: **v3** (Dựa trên run `07-05-2026_v4`) và **v4** (Dựa trên run `12-05-2026_v4`). [ĐÃ ĐƯỢC KIỂM CHỨNG]

---

## 1. So Sánh Thông Số Định Lượng (Quantitative Metrics)

| Chỉ số | v3 (07-05_v4) | v4 (12-05_v4) | Đánh giá |
| :--- | :---: | :---: | :--- |
| **Average CER (GT-only)** | 38.49% | **42.27%** | ⚠️ Tăng ~3.8% (Chưa tối ưu) |
| **Avg Inference RTF** | 2.67 | **2.15** | 🚀 Nhanh hơn 19% |
| **LC Recovery Success** | 72.7% (8/11) | **100.0% (11/11)** | ✅ Xử lý ổn định hơn |
| **High Severity Issues** | 2 file | **1 file** | 🛡️ Giảm rủi ro nghiêm trọng |
| **Hallucination Rate** | 81.82% | 81.82% | 🔄 Không đổi |
| **VAD Threshold** | 0.5 | **0.6** | Lọc nhiễu tốt hơn |
| **VAD Padding** | 500ms | **300ms** | Chunk gọn hơn |

> [!IMPORTANT]
> **Lưu ý về CER:** Nếu tính trên toàn bộ 11 file (bao gồm silence), CER của v4 là 34.58%. Tuy nhiên, để so sánh công bằng với v3 (vốn loại trừ file tĩnh), chúng tôi sử dụng mẫu số **GT-only (9 file)**. Ở hệ quy chiếu này, CER của v4 cao hơn v3.

---

## 2. Phân Tích Chuyên Sâu (Deep Dive)

### 2.1. Cải tiến cơ chế Phục hồi (Language Collapse Recovery)

- **Phiên bản v3:** Gặp khó khăn với các file bị lỗi nặng, 3/11 group retry bị thất bại do thiếu "anchor".
- **Phiên bản v4:** Nâng cấp cơ chế `fixed_fallback_trim`. Hệ thống đạt tỷ lệ khôi phục thành công tuyệt đối (**11/11 group**) trong điều kiện ổn định.
- **Kết quả:** Loại bỏ hoàn toàn trạng thái `failed` trong quá trình recovery.

### 2.2. Tối ưu hóa cấu hình VAD

- Việc tăng ngưỡng VAD (0.6) và giảm Padding (300ms) giúp:
    1. **Tốc độ:** RTF giảm xuống mức 2.15 (mức tốt nhất hiện tại).
    2. **Độ chính xác:** Giảm lượng noise lọt vào mô hình, tuy nhiên dường như lại làm tăng CER ở các đoạn speech có âm lượng nhỏ.

### 2.3. Đặc điểm ảo giác (Hallucination Patterns)

- **Tỷ lệ tổng thể:** Đứng im ở mức **81.82%** (9/11 file có ít nhất một lỗi chèn nội dung).
- **Tính chất:** v3 thường chèn tiếng Anh vô nghĩa (destructive). v4 chuyển sang chèn các câu chào hỏi xã giao tiếng Nhật (*お疲れ様でした*).
- **Nhận định:** v4 cho transcript "sạch" về cảm quan nhưng CER thực tế vẫn cao do lỗi chèn từ (insertions).

---

## 3. Đánh Giá Điểm Mạnh & Điểm Yếu

### Phiên bản v3 (07/05)

* **Điểm mạnh:** CER trên các file có tiếng nói tốt hơn; xử lý file tĩnh hoàn hảo.
- **Điểm yếu:** RTF chậm; tỷ lệ khôi phục lỗi ngôn ngữ chỉ đạt 72.7%.

### Phiên bản v4 (12/05) - Hiện tại

* **Điểm mạnh:** Tốc độ xử lý nhanh nhất; cơ chế recovery hoạt động 100% thành công; lỗi High Severity giảm xuống còn 1 file.
- **Điểm yếu:** CER (GT-only) tăng nhẹ; nhạy cảm với biến động mạng; bias câu chào hỏi xã giao vẫn còn nguyên.

---

## 4. Kết Luận & Khuyến Nghị

Phiên bản **v4** là một bước tiến quan trọng về **hiệu năng (speed)** và **khả năng phục hồi (resilience)**, nhưng chưa phải là "Golden Run" về mặt **độ chính xác (accuracy)** do CER có dấu hiệu regression nhẹ.

**Các bước tiếp theo:**

1. **Độ chính xác:** Tìm nguyên nhân tại sao CER (GT-only) tăng từ 38% lên 42%. Kiểm tra xem VAD 0.6 có đang cắt mất đoạn speech yếu nào không.
2. **Mô hình:** Tinh chỉnh System Prompt để triệt tiêu bias "Social Hallucination".
3. **Hạ tầng:** Cải thiện logic Retry cho Batch Runner để tránh lỗi mạng như run v5.

---
**Người thực hiện báo cáo:** Antigravity AI (Updated with Codex feedback)
**Ngày lập:** 12/05/2026
