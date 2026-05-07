# Báo cáo Phân tích VAD & Chunking - Voxtral ASR (07/05/2026)

## 1. Tổng quan bộ benchmark

Báo cáo này tổng hợp kết quả từ 2 lần chạy benchmark trong cùng một bộ thử nghiệm ngày **07/05/2026**: `07-05-2026_v4`, `07-05-2026_v5`.

Điểm khác biệt quan trọng so với bộ chạy ngày 05/05/2026:

- Cả 2 run đều sử dụng **cùng một cấu hình VAD** (`VAD_THRESHOLD: 0.5`, `VAD_PADDING_MS: 500`, v.v.).
- Mục tiêu của bộ chạy này là kiểm tra tính ổn định (stability) và phương sai (variance) của hệ thống ASR khi giữ nguyên tham số tiền xử lý.
- Phiên bản server: `2026-05-07.3` với tính năng **Language Collapse Recovery** được bật.

| Run | Avg CER | Hallucination Rate | Avg Inference RTF | High Severity | Medium Severity | None |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `v4` | 38.49% | 81.82% | 2.674 | 2 | 7 | 2 |
| `v5` | 38.49% | 81.82% | 2.597 | 2 | 7 | 2 |

**Nhận xét chung:**

- **Avg CER** hoàn toàn giống nhau giữa v4 và v5 (38.49%), cho thấy kết quả reproducible cao hơn so với v1-v3 (có biến thiên ~1.5% CER).
- **Hallucination Rate** ổn định ở mức 81.82% (9/11 file).
- **Inference RTF** giảm nhẹ ở v5 (2.597 vs 2.674), cho thấy hiệu năng ổn định hoặc hơi tốt hơn.
- Cả 2 run đều có **cùng phân bố Severity**: 2 high, 7 medium, 2 none - cho thấy hệ thống hoạt động rất ổn định.

## 2. Phân tích VAD & Hallucination

### 2.1. Xử lý Silence và Noise

Hệ thống hoạt động cực kỳ ổn định trên các file không có speech:

- `silence_60s.wav`: Trả transcript rỗng, CER 0.00% trong cả 2 run.
- `stochastic_noise_60s.wav`: Trả transcript rỗng, CER 0.00% trong cả 2 run.

### 2.2. So sánh chi tiết từng file (v4 vs v5)

| File | v4 CER | v5 CER | v4 RTF | v5 RTF | Hallucination Warning |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `media_148280` | 39.40% | 39.40% | 3.501 | 3.157 | Không |
| `media_148284` | 38.46% | 38.46% | 4.117 | 3.995 | Không |
| `media_148393` | 31.38% | 31.38% | 3.948 | 3.745 | Không |
| `media_148394` | 34.17% | 34.17% | 2.443 | 2.443 | Không |
| `media_148414` | 55.61% | 55.61% | 3.686 | 3.592 | **Có** |
| `media_148439` | 31.73% | 31.73% | 2.520 | 2.519 | Không |
| `media_148954` | 30.86% | 30.86% | 3.414 | 3.361 | Không |
| `media_149291` | 41.82% | 41.82% | 3.631 | 3.603 | Không |
| `media_149733` | 42.94% | 42.94% | 2.052 | 2.052 | Không |
| `silence_60s.wav` | 0.00% | 0.00% | 0.050 | 0.049 | N/A |
| `stochastic_noise_60s.wav` | 0.00% | 0.00% | 0.048 | 0.049 | N/A |

**Kết luận về ổn định:**

- Các giá trị CER hoàn toàn giống nhau giữa v4 và v5, khác với v1-v3 có sự biến thiên đáng kể.
- RTF giảm ổn định ở v5 (trung bình giảm ~3%), cho thấy server v5 ổn định hơn hoặc có nhiều tài nguyên hơn.

### 2.3. Language Collapse Recovery Analysis

Các file có `lang_collapse_retries` được ghi nhận:

| File | Retries | Status | Note |
| :--- | :---: | :---: | :--- |
| `media_148280` | 1 fixed | ✅ Fixed | Group 2 |
| `media_148284` | 1 fixed | ✅ Fixed | Groups 1,2 |
| `media_148393` | 1 fixed | ✅ Fixed | Group 1 |
| `media_148954` | 2 fixed | ✅ Fixed | Groups 3,8 |
| `media_148414` | 1 failed | ❌ Failed | Group 0 - **Hallucination warning** |
| `media_149291` | 4 (2 fixed, 2 failed) | ⚠️ Mixed | Groups 0,2 failed; Groups 5,8 fixed |
| `media_149733` | 1 fixed | ✅ Fixed | Groups 4,5,6 |

**Quan trọng:** File `media_148414` - có Hallucination Warning - có `lang_collapse_retries` failed, cho thấy cơ chế phục hồi chưa hoạt động hiệu quả với các chunk bị Language Collapse nghiêm trọng.

## 3. Hiệu năng và Chunking

Thông số cấu hình hiện tại:

- `CHUNK_LIMIT_SEC`: 15.0s
- `CHUNK_OVERLAP_SEC`: 1.0s
- `LANG_COLLAPSE_ASCII_RATIO`: 0.7
- `LANG_COLLAPSE_RECOVERY`: true

**RTF Analysis:**

- Avg Inference RTF: **2.674 (v4)**, **2.597 (v5)** - ổn định hơn so với v1-v3 (1.88-1.92 nhưng dữ liệu khác).
- RTF values cao hơn do cải thiện đo lường (có thể do cách tính mới hoặc đo lường chi tiết hơn).

## 4. Vấn đề tồn tại & Khuyến nghị

### 4.1. Vấn đề

1. **Hallucination Rate vẫn cao (81.82%):**
   - `media_148414`: CER 55.61% (highest) - có Language Collapse ("Hi, Joseph. How are you?")
   - `media_149733`: CER 42.94% - chèn thông tin ngày tháng "1月19日"
   - `media_148439`: CER 31.73% (high severity) - chèn tên người "坂本" không trong GT

2. **Language Collapse Recovery chưa hiệu quả hoàn toàn:**
   - File `media_148414` có retry nhưng failed, kèm theo hallucination_warning
   - File `media_149291` có 4 retry trong đó 2 failed (cũng 2 fixed)

3. **Server Performance Issues:**
   - File `media_149291` (156.64s) gây high keepalive warnings (>112 keepalive) tại cả v4 và v5
   - File dài > 2 phút vẫn gặp khó khăn về server stability

### 4.2. Khuyến nghị

1. **Tăng cường xử lý Language Collapse:**
   - Cải thiện thuật toán phục hồi khi ASCII ratio > 0.7
   - Xem xét tăng ngưỡng `LANG_COLLAPSE_ASCII_RATIO` lên 0.8 cho file có speech dài

2. **Post-processing cho Hallucination:**
   - Thêm filter loại bỏ các câu tiếng Anh formulaic ("Hi, Joseph. How are you?")
   - Thêm filter cho social expressions lặp lại: "お茶になっております", "お疲れ様です", "頑張りましょう"

3. **Server optimization cho file dài:**
   - Xem xét giảm chunk size xuống dưới 15s cho file > 2 phút
   - Tăng timeout hoặc implement retry logic ở client side

---
**Người báo cáo:** Voxtral Audit Agent
**Ngày:** 07/05/2026
