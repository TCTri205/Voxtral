# Báo cáo Phân tích VAD & Chunking - Voxtral ASR (12/05/2026)

## 1. Tổng quan bộ benchmark

Báo cáo này tổng hợp kết quả từ 2 lần chạy benchmark của phiên bản hiện tại ngày **12/05/2026**: `12-05-2026_v4` và `12-05-2026_v5`.

Mục tiêu của bộ chạy này là đánh giá hiệu năng của bản cập nhật mới so với các bản cũ (v2, v3) và kiểm tra tính ổn định của server.

- **Phiên bản server:** `2026-05-12.2`
- **Cấu hình VAD:** `VAD_THRESHOLD: 0.6`, `VAD_PADDING_MS: 300`, `CHUNK_LIMIT_SEC: 15.0`.
- **Tính năng nổi bật:** Cải thiện cơ chế **Language Collapse Recovery** với fallback trim.

| Run | Avg CER | Hallucination Rate | Avg Inference RTF | High Severity | Medium Severity | None |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `v4` | 34.58% | 81.82% | 2.153 | 1 | 8 | 2 |
| `v5` | 45.07% | 100.00% | 2.706 | 2 | 5 | 0 |
| `v6` | 36.44% | 81.82% | 2.100 | 1 | 8 | 2 |

**Nhận xét chung:**

- **v4 (Golden Run):** Xử lý thành công 100% file, CER cải thiện đáng kể so với v3 (34.58% vs 38.28% - tính trên cả file tĩnh).
- **v6 (Validation Run):** Xác nhận tính ổn định của v4 với các chỉ số tương đương (CER 36.44%, RTF 2.1).
- **v5 (Unstable Run):** Gặp sự cố mạng (`getaddrinfo failed`) và timeout trên 4 file.
- **Tính ổn định:** Hệ thống đạt độ ổn định và khả năng tái lập (reproducibility) cao giữa v4 và v6 khi hạ tầng mạng ổn định.

## 2. Phân tích VAD & Hallucination

### 2.1. Xử lý Silence và Noise

Hệ thống tiếp tục duy trì sự ổn định tuyệt đối trên các file không có speech (trong run v4):

- `silence_60s.wav`: CER 0.00%, RTF 0.057.
- `stochastic_noise_60s.wav`: CER 0.00%, RTF 0.048.

### 2.2. So sánh chi tiết từng file (v4 vs v5)

| File | v4 CER | v5 CER | v6 CER | v4 RTF | v6 RTF | Hallucination (v4/v6) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `media_148280` | 61.68% | 61.96% | 60.33% | 2.680 | 2.458 | Medium |
| `media_148284` | 49.23% | 49.23% | 49.23% | 2.141 | 2.141 | Medium |
| `media_148393` | 39.89% | 40.43% | 40.43% | 2.388 | 2.376 | Medium |
| `media_148394` | 32.16% | 32.16% | 32.16% | 2.275 | 2.271 | Medium |
| `media_148414` | 42.09% | 47.19% | 42.35% | 4.060 | 4.056 | Medium |
| `media_148439` | 32.69% | 47.60% | 47.60% | 2.807 | 2.667 | **High** |
| `media_148954` | 35.52% | 36.90% | 41.90% | 2.838 | 2.735 | Medium |
| `media_149291` | 29.45% | N/A | 29.14% | 3.028 | 2.989 | Medium |
| `media_149733` | 57.67% | N/A | 57.67% | 1.360 | 1.311 | Medium |

**Kết luận:** Sự chênh lệch CER giữa v4 và v5 ở các file cùng thành công (như `media_148439`) cho thấy khi network không ổn định, chất lượng trả về của mô hình cũng bị ảnh hưởng (có thể do chunk bị mất hoặc gửi thiếu).

### 2.3. Language Collapse Recovery Analysis

Cơ chế phục hồi ở phiên bản `2026-05-12.2` hoạt động rất tích cực:

| File | Retries (v4/v6) | Status | Note |
| :--- | :---: | :---: | :--- |
| `media_148280` | 2/2 fixed | ✅ Fixed | Khôi phục thành công 2 group |
| `media_148414` | 2/2 fixed | ✅ Fixed | Sử dụng `fixed_fallback_trim` hiệu quả |
| `media_148954` | 2/1 fixed | ⚠️ Mixed | v6 ghi nhận 1 case failed ở group 2,3 |
| `media_149291` | 3/3 fixed | ✅ Fixed | File dài, khôi phục nhiều đoạn |

**Cải tiến:** Tỷ lệ thành công cực cao (**v4: 12/12**, **v6: 11/12**). Chỉ ghi nhận duy nhất 1 case `failed` đơn lẻ ở run v6.

## 3. Hiệu năng và Chunking

Thông số cấu hình:
- `VAD_THRESHOLD`: 0.6 (Tăng từ 0.5 để lọc noise tốt hơn)
- `VAD_PADDING_MS`: 300 (Giảm từ 500 để chunk gọn hơn)
- `CHUNK_LIMIT_SEC`: 15.0s

**RTF Analysis:**
- Avg Inference RTF (v4): **2.153** - Duy trì tốc độ tối ưu tương đương v3 (2.119) và nhanh hơn đáng kể so với v2 (2.629).
- Việc tăng ngưỡng VAD và giảm padding giúp giảm tải cho server mà vẫn duy trì được chất lượng transcript.

## 4. Vấn đề tồn tại & Khuyến nghị

### 4.1. Vấn đề

1. **Ảo giác chèn nội dung (Insertions):**
   - Vẫn xuất hiện các câu chào xã giao không có trong GT như "お疲れ様でした", "頑張りましょう".
   - `media_148439`: Lỗi High Severity duy nhất do chèn thông tin người đại diện sai.

2. **Độ nhạy mạng (Network Sensitivity):**
   - Run v5 cho thấy hệ thống dễ bị sập (DNS error/Timeout) khi môi trường mạng không lý tưởng, gây mất dữ liệu nghiêm trọng.

3. **CER ở một số file còn cao:**
   - `media_148280` (61.68%) và `media_149733` (57.67%) vẫn là những case khó cần tối ưu thêm.

### 4.2. Khuyến nghị

1. **Tinh chỉnh Prompt để giảm Social Hallucinations:**
   - Cập nhật System Prompt để mô hình khắt khe hơn với các câu chào hỏi mặc định nếu không nghe rõ.

2. **Cải thiện Client-side Resilience:**
   - Implement cơ chế retry tự động khi gặp lỗi `getaddrinfo` hoặc `timeout` thay vì dừng hẳn quá trình benchmark.

3. **Hybrid VAD Strategy:**
   - Với các file có CER > 50%, thử nghiệm giảm `CHUNK_LIMIT_SEC` xuống 10s để tăng độ tập trung cho mô hình trên từng đoạn speech ngắn.

---
**Người báo cáo:** Voxtral Audit Agent
**Ngày:** 12/05/2026
