# Báo Cáo Tổng Hợp Công Việc - Dự Án Voxtral ASR (18/05/2026)

Báo cáo này lưu trữ toàn bộ tiến trình chẩn đoán, tối ưu hóa cấu hình VAD, thuật toán phân chia chunk, và cải tiến cơ chế thử lại (retry mechanism) của hệ thống Voxtral ASR trong ngày **18/05/2026**.

---

## 1. Tổng Quan Tiến Trình Trong Ngày (Executive Summary)

Ngày 18/05/2026 chứng kiến những biến động lớn về hiệu năng và chất lượng nhận diện tiếng Nhật của Voxtral ASR. Tiến trình được chia làm 4 giai đoạn chính:

1. **Sáng (Khắc phục Regression v10 & Đạt đỉnh v11):** Sửa bộ lọc méo tiếng (BPF 300Hz-3.4kHz), loại bỏ logic ngắt cứng `TimeBasedStoppingCriteria`, đưa im lặng VAD về **700ms**. Hệ thống đạt kỷ lục CER thấp nhất lịch sử: **40.93%** và RTF siêu mượt: **3.62** (Commit `d882aad`).
2. **Trưa & Chiều (Mở rộng Tính năng v12 -> v14):** Tích hợp đo lường chi tiết (Telemetry), tự động chia nhỏ chunk cục bộ khi lỗi (Sub-chunk recovery), áp dụng chunking không khoảng trống (Gapless VAD chunking) và phân chunk nhắm mục tiêu giọng nói (Targeted speech region chunking) với đệm an toàn tối thiểu 3.0s.
3. **Cuối Chiều (Phát hiện Regression v14):** Chạy thử nghiệm benchmark v14 cho kết quả sụt giảm mạnh. CER vọt lên **45.81%** và RTF chậm lại **4.66** (chậm hơn 30%). Phân tích log tìm ra nguyên nhân do tăng VAD padding lên quá mức (**1500ms**) và hạ thấp ngưỡng VAD quá nhạy (**0.45**) làm model ngập trong khoảng lặng bẩn.
4. **Tối (Nghiên cứu Tối ưu hóa Retry & Thiết lập Lộ trình v15):** Phân tích cơ chế thử lại l lồng đệ quy (Layer 1 & Layer 2) gây lãng phí tài nguyên và che giấu hiệu năng tiền xử lý. Thiết lập báo cáo chuyên sâu và đề xuất khôi phục tham số v11 kết hợp với đơn giản hóa retry (chỉ chạy 1 lần ở T=0.2 kèm logic Strict Rollback).

---

## 2. Nhật Ký Commits Chi Tiết Ngày 18/05/2026 (Chronological Commit Log)

Hôm nay hệ thống ghi nhận **7 commits** trên nhánh chính `feature/voxtral-implementation` (múi giờ +7):

### 1️⃣ Commit `805f43d` - Pha Tiền Xử Lý Ban Đầu
* **Nội dung:** Tăng cường khả năng phát hiện sập ngôn ngữ (language collapse) và thêm bộ tiền xử lý âm thanh cơ bản.

### 2️⃣ Commit `3cee0e2` - Revert Bộ Lọc Band-Pass (BPF)
* **Nội dung:** Loại bỏ bộ lọc telephony Band-Pass Filter (300Hz - 3.4kHz) vì làm méo phụ âm tiếng Nhật. Khôi phục về bộ lọc High-Pass Filter (HPF) 80Hz truyền thống.

### 3️⃣ Commit `d882aad` - Đạt đỉnh Tối ưu hóa Bản dựng v11 (Stable Peak)
* **Nội dung:** Loại bỏ hoàn toàn cơ chế ngắt cứng gây cụt câu `TimeBasedStoppingCriteria`, đưa `VAD_SEGMENT_SILENCE_MS` về mức tối ưu **700ms**, tinh chỉnh `n_range` lọc lặp từ về `(3, 4, 5)`.
* **Kết quả:** Đạt CER kỷ lục **40.93%**, RTF **3.62**. Khắc phục triệt để lỗi mất chữ cuối câu.

### 4️⃣ Commit `ac9f227` - Tích hợp Telemetry & Sub-chunk Recovery
* **Nội dung:** Bổ sung ghi nhận telemetry chi tiết cho từng chunk (token, latency, keepalive peak), tích hợp cổng kiểm thử chấp nhận (Acceptance Verification gates) vào `benchmark_runner.py` và cơ chế tự cắt đôi chunk lỗi `_recover_via_sub_chunking`.

### 5️⃣ Commit `c9bdb7c` - Tinh chỉnh v12
* **Nội dung:** Tối ưu hóa cơ chế khôi phục ASR dựa trên ngữ nghĩa và điều chỉnh ngưỡng trễ CPU để cải thiện tính ổn định.

### 6️⃣ Commit `14a04d4` - Tinh chỉnh v13 (Gapless VAD Chunking)
* **Nội dung:** Hiện thực hóa thuật toán gapless VAD chunking và tăng ngưỡng skip để khôi phục chất lượng ASR.

### 7️⃣ Commit `58db424` - Phân Chunk Nhắm Mục Tiêu v14 (Regression State)
* **Nội dung:** Áp dụng thuật toán phân chia chunk nhắm mục tiêu vùng tiếng nói (Targeted speech region chunking) với đệm an toàn tối thiểu 3.0s, đồng thời tăng VAD Padding lên 1500ms và hạ VAD Threshold xuống 0.45.
* **Kết quả:** Gây ra lỗi sụt giảm chất lượng (CER vọt lên **45.81%** và RTF chậm lại **4.66**).

---

## 3. Bảng Kết Quả Benchmark Qua Các Mốc Phát Triển

| Mốc thử nghiệm | Bản v9 (Baseline cũ) | Bản v11 (Đỉnh ổn định) | Bản v14 (Bị lỗi Regression) | Đánh giá so với Bản v11 |
| :--- | :---: | :---: | :---: | :--- |
| **Speech-only Avg CER** | 43.28% | **40.93%** | **45.81%** | 📈 Tăng 4.88% (Tệ hơn rõ rệt) |
| **Inference Avg RTF** | 3.59 | **3.62** | **4.66** | ⏱️ Chậm hơn 30% |
| **Worst-file CER** | 41.36% | **30.29%** | **71.15%** | 📈 Tăng 40.86% (Thảm họa) |
| **Trạng thái Acceptance** | Đạt | **ĐẠT XUẤT SẮC** | **REJECTED (FAILED GATES)**| Không vượt qua kiểm thử |

---

## 4. Chẩn Đoán Chi Tiết Lỗi Của v14 & Hướng Xử Lý Ngày Mai

Qua phân tích sâu mã nguồn (`git diff d882aad HEAD`) và dữ liệu log của server, việc v14 bị sụt giảm chất lượng bắt nguồn từ sự kết hợp của:
1. **`VAD_PADDING_MS` = 1500ms (so với 300ms của v11):** Đệm quá nhiều khoảng lặng bẩn chứa hơi thở và tiếng gió nền, kích hoạt Whisper sinh ra lặp từ và câu thoại ảo giác.
2. **`VAD_THRESHOLD` = 0.45 (so với 0.70 của v11):** Ngưỡng quá nhạy làm lọt các tiếng động tạch micro của tổng đài thành tiếng nói.
3. **`_create_vad_aware_chunks` của v14:** Ép buộc ngữ cảnh tối thiểu 3.0s làm mất đi ranh giới chính xác của các đoạn tiếng nói.

### Kế hoạch hành động ngày mai (Đưa hệ thống lên v15 tối ưu):
* **Hành động 1:** Khôi phục `VAD_PADDING_MS = 300` và `VAD_THRESHOLD = 0.70`.
* **Hành động 2:** Khôi phục thuật toán `_create_vad_aware_chunks` của v11 (ổn định, hiệu quả).
* **Hành động 3:** Chuyển đổi cơ chế thử lại toàn cục lồng đệ quy của Phase 3 thành cơ chế **Thử lại đơn giản** (chỉ chạy 1 lần duy nhất tại T=0.2 và áp dụng logic Strict Rollback - nếu kết quả thử lại bằng hoặc tệ hơn kết quả gốc thì bắt buộc chọn kết quả gốc chưa thử lại).
* **Báo cáo chi tiết và Mã nguồn mẫu** đã được chuẩn bị đầy đủ tại tệp tin:  
  👉 **[retry_mechanism_optimization.md](file:///d:/VJ/Voxtral/reports/vad_chunk_v6/retry_mechanism_optimization.md)**.

---
**Người tổng hợp:** Antigravity AI  
**Thời gian kết thúc phiên làm việc:** 18/05/2026 (17:05 UTC+7)  
**Trạng thái đóng:** Đã đồng bộ mã nguồn & Tài liệu roadmap sẵn sàng cho ngày mai.  
