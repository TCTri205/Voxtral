# Kế hoạch Hoàn thiện VAD & Hallucination Recovery (v4)

Báo cáo này đối chiếu kết quả benchmark ngày 12/05 (`v2`, `v3`) và đưa ra kế hoạch hành động cuối cùng để tối ưu chất lượng ASR.

## 1. Phân tích & Đối chiếu (Analysis & Comparison)

Dựa trên dữ liệu thực tế từ các lần chạy gần nhất:

| Phiên bản | VAD (Thres/Pad) | Avg CER | Tình trạng Hallucination (media_148414) |
| :--- | :--- | :--- | :--- |
| **07/05 (v3)** | 0.5 / 500ms | 38.49% | Bị "Hi, Joseph" |
| **12/05 (v3)** | 0.65 / 300ms | 46.78% | Vẫn bị "Hi, Joseph" |

### Nhận xét:
1. **VAD Tuning đơn thuần đã chạm ngưỡng**: Tăng Threshold lên 0.65 không những không diệt được ảo giác "Hi, Joseph" (do model sinh ra từ noise cực nhỏ) mà còn làm **CER tăng vọt** (từ 38% lên 46%) do mất dữ liệu âm thanh quan trọng.
2. **Cần Logic Recovery mạnh hơn**: Kết quả `v3` ngày 12/05 cho thấy Recovery Phase 2 bị `failed` trên Chunk 0 vì thiếu cơ chế fallback đủ mạnh.

---

## 2. Kế hoạch Hành động (Implementation Plan)

Chúng ta sẽ implement Phase 2 Recovery hoàn chỉnh theo các bước sau:

### 2.1. Điều chỉnh lại tham số VAD (Rollback & Optimize)
Để đưa CER trở lại mức ổn định (< 40%), chúng ta sẽ nới lỏng VAD một chút nhưng vẫn giữ chặt hơn mức 0.5 cũ.
- `VAD_THRESHOLD`: **0.60**
- `VAD_PADDING_MS`: **300ms**
- `VAD_MIN_SPEECH_DURATION_MS`: **400ms**

### 2.2. Nâng cấp Cơ chế Recovery (Phase 2)
Cập nhật `voxtral_server_transformers.py` với 2 cải tiến then chốt:

1. **Temperature Shift (0.5)**: 
   - Khi phát hiện Language Collapse (ASCII ratio > 0.7), các lượt inference retry sẽ sử dụng `temperature: 0.5`.
   - Mục tiêu: Giúp model thoát khỏi "vòng lặp" xác suất dẫn đến tiếng Anh/ảo giác.

2. **Fallback Trim (500ms) cho Chunk 0**:
   - Nếu Retry với Anchor vẫn thất bại (vẫn ra tiếng Anh), hệ thống sẽ thực hiện:
     - Cắt bỏ 500ms đầu tiên của audio chunk đó.
     - Inference lại audio đã cắt.
   - Mục tiêu: Loại bỏ hoàn toàn các đoạn nhiễu/thở ở cực đầu file - tác nhân chính gây ảo giác.

---

## 3. Các bước Thực hiện (Execution Steps)

1. **Modify Server**: Cập nhật logic trong `voxtral_server_transformers.py`.
2. **Unit Test**: Chạy test riêng file `media_148414`. Kỳ vọng: Transcript bắt đầu bằng tiếng Nhật, status `fixed_fallback_trim`.
3. **Benchmark Verification**: Chạy lại toàn bộ 11 file. Kỳ vọng: CER < 40% và 0 file bị ảo giác tiếng Anh ở đầu.

---
**Người lập kế hoạch:** Voxtral AI Assistant
**Ngày:** 12/05/2026
