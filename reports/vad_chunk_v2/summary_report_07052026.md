# Báo cáo Phân tích VAD & Chunking - Voxtral ASR (07/05/2026)

## 1. Tổng quan bộ benchmark

Báo cáo này tổng hợp kết quả từ 3 lần chạy benchmark trong cùng một bộ thử nghiệm ngày **07/05/2026**: `07-05-2026_v1`, `07-05-2026_v2`, `07-05-2026_v3`. 

Điểm khác biệt quan trọng so với bộ chạy ngày 05/05/2026:
- Cả 3 run đều sử dụng **cùng một cấu hình VAD** (`VAD_THRESHOLD: 0.5`, `VAD_PADDING_MS: 500`, v.v.). 
- Mục tiêu của bộ chạy này là kiểm tra tính ổn định (stability) và phương sai (variance) của hệ thống ASR khi giữ nguyên tham số tiền xử lý.

| Run | Avg CER | Hallucination Rate | Avg Inference RTF | High Severity | Medium Severity | None |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `v1` | 38.55% | 81.82% | 1.922 | 4 | 5 | 2 |
| `v2` | 37.80% | 81.82% | 1.889 | 2 | 7 | 2 |
| `v3` | 37.04% | 81.82% | 1.881 | 4 | 5 | 2 |

**Nhận xét chung:**
- **Avg CER** cải thiện nhẹ qua các lần chạy (từ 38.55% xuống 37.04%), mặc dù cấu hình không đổi. Điều này cho thấy có sự biến thiên tự nhiên trong quá trình decoding/inference.
- **Hallucination Rate** ổn định ở mức 81.82% (9/11 file).
- **v2** là run có kết quả tốt nhất về mặt **Severity**, chỉ có 2 trường hợp lỗi nghiêm trọng (High), so với 4 trường hợp ở `v1` và `v3`.

## 2. Phân tích VAD & Hallucination

### 2.1. Xử lý Silence và Noise
Hệ thống hoạt động cực kỳ ổn định trên các file không có speech:
- `silence_60s.wav`: Trả transcript rỗng, CER 0.00% trong cả 3 run.
- `stochastic_noise_60s.wav`: Trả transcript rỗng, CER 0.00% trong cả 3 run.

**Cải thiện quan trọng:** Lỗi đánh giá nhầm của LLM Evaluator ở phiên bản trước (gán `high` severity cho silence) đã được khắc phục. Hiện tại cả 2 file này đều được đánh giá là `none`.

### 2.2. Biến thiên kết quả (Variance Analysis)
Mặc dù cấu hình VAD giống nhau, các file speech vẫn có sự thay đổi về nội dung nhận diện:

| File | v1 CER | v2 CER | v3 CER | Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| `media_148284` | 58.46% | 58.46% | 34.62% | `v3` cải thiện vượt trội (giảm insertion 'そうですね') |
| `media_148439` | 36.54% | 32.69% | 31.73% | Xu hướng cải thiện CER qua các run |
| `media_149733` | 57.67% | 56.75% | 61.04% | `v3` bị tụt chất lượng (nhiều insertion về ngày tháng) |

### 2.3. Các lỗi Hallucination điển hình (Chưa khắc phục)
- **Language Collapse:** Chèn tiếng Anh không liên quan (ví dụ: `Hi, Joseph. How are you?` trong `media_148414`).
- **Phonetic Insertion:** Các cụm từ xã giao như `頑張りましょう`, `お疲れ様です`, `お茶になっております` thường xuyên bị chèn vào khi không có trong GT.
- **Contextual Collapse:** Lỗi `Just the Asaga` vẫn xuất hiện trong `media_149291`.

## 3. Hiệu năng và Chunking

Thông số cấu hình hiện tại:
- `CHUNK_LIMIT_SEC`: 15.0s
- `CHUNK_OVERLAP_SEC`: 1.0s

**RTF Analysis:**
- Avg Inference RTF duy trì ở mức **1.88 - 1.92**.
- Overhead của pipeline (Total RTF - Inference RTF) rất thấp (~0.02), khẳng định cơ chế chunking và merging hoạt động hiệu quả về mặt tài nguyên.

## 4. Vấn đề tồn tại & Khuyến nghị

### 4.1. Vấn đề
1. **Sự không nhất quán (Non-determinism):** Cùng một cấu hình nhưng CER có thể lệch tới 20% trên cùng một file (`media_148284`). Điều này gây khó khăn cho việc tinh chỉnh tham số VAD vì nhiễu từ mô hình ASR quá lớn.
2. **High Severity trong Speech:** Vẫn còn 2-4 file bị lỗi nặng (sai lệch hoàn toàn nội dung hoặc chèn đoạn hội thoại lạ).
3. **Lỗi lặp từ (Repetition):** Đã phân tích kỹ lỗi lặp trong `media_148280` và `media_148414`. Kết luận lỗi phần lớn do **ASR Model Hallucination** (model tự chèn hoặc lặp từ trong quá trình decoding) hơn là do lỗi ghép nối chunk.

### 4.2. Khuyến nghị
1. **Lựa chọn cấu hình:** Sử dụng các tham số của bộ chạy này làm baseline ổn định. Nếu ưu tiên tính an toàn (giảm lỗi nặng), `v2` là trạng thái tốt nhất để phân tích sâu.
2. **Xử lý Hallucination:** Cần tập trung vào việc lọc các cụm từ tiếng Anh hoặc các câu xã giao lặp đi lặp lại ở bước hậu xử lý (Post-processing) thay vì cố gắng sửa bằng VAD.
3. **Mở rộng Benchmark:** Thử nghiệm với `VAD_THRESHOLD` cao hơn (ví dụ 0.6 hoặc 0.65) để xem liệu có thể giảm bớt các đoạn noise gây hallucination mà không gây deletion hay không.

---
**Người báo cáo:** Voxtral Audit Agent
**Ngày:** 07/05/2026
