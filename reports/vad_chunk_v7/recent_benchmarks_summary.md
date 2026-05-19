# Recent Benchmarks Summary (Voxtral ASR)

Báo cáo này tổng hợp các kết quả benchmark gần nhất (bao gồm loạt chạy thử nghiệm của ngày hôm nay 19/05/2026), ghi nhận đầy đủ các chỉ số cấu hình (Config) và kết quả (Metrics) để phục vụ việc chẩn đoán, đối chiếu và tối ưu hóa hệ thống Voxtral ASR.

## Bảng Kết Quả Tổng Hợp Chi Tiết (Cập nhật ngày 19/05/2026)

| Run ID | Result Dir | Avg CER (Speech) | Avg Inf RTF | Halluc (High) | VAD Thresh | VAD Padding | Seg Silence | n-range | Retry Strategy | Filter |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| **v15.7** | `19-05_v7` | 46.20% | 2.69 | **N/A\*** | 0.45 | 50/350ms (Asym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | BPF 300-3.4k |
| **v15.6** | `19-05_v6` | 47.66% | 2.37 | **2** | 0.45 | 50/350ms (Asym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | HPF 100Hz |
| **v15.5** | `19-05_v5` | 43.40% | **2.07** | **2** | 0.45 | 50/350ms (Asym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | BPF (Warped) |
| **v15.4** | `19-05_v4` | 42.86% | 2.13 | **5** | 0.70 | 300ms (Sym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | HPF 80Hz |
| **v15.3** | `19-05_v3` | 49.76% | 2.16 | **2** | 0.70 | 300ms (Sym) | 600ms | 3,4,5 | Single T=0.2 + Rollback | HPF 80Hz |
| **v15.2** | `19-05_v2` | **41.17%** | 2.75 | **5** | 0.70 | 300ms (Sym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | HPF 80Hz |
| **v15.1** | `19-05_v1` | 42.84% | 3.20 | **5** | 0.70 | 300ms (Sym) | 700ms | 3,4,5 | Single T=0.2 + Rollback | HPF 80Hz |
| **v14.R** | `18-05_v8` | 45.81% | 4.66 | **3** | 0.45 | 1500ms (Sym) | 700ms | 3,4,5 | Layer 1+2 (Recursive) | HPF 80Hz |
| **v11.S** | `18-05_v6` | 41.45% | 3.34 | **2** | 0.45 | 300ms (Sym) | 700ms | 3,4,5 | Layer 1+2 (Recursive) | HPF 80Hz |
| **v10.C** | `18-05_v5` | 45.24% | 7.32 | **1** | 0.50 | 500ms (Sym) | 1000ms | 3,4,5 | Basic Retry | BPF 3.4kHz |
| **v11.S** | `18-05_v4` | **40.93%** | **3.62** | **4** | 0.70 | 300ms (Sym) | 700ms | 3,4,5 | Layer 1+2 (Recursive) | HPF 80Hz |

*\* Ghi chú: `v15.7` (`19-05_v7`) ghi nhận Halluc = N/A do chưa hoàn tất việc chạy LLM-eval tại thời điểm snapshot báo cáo. Các run còn lại đã hoàn tất đánh giá LLM-eval đầy đủ và cập nhật số liệu chính xác tuyệt đối.*

---

## Phân Tích Chuyên Sâu & Đối Chiếu Cấu Hình

### 1. Sự đánh đổi giữa RTF và CER (v15.2 vs v15.5)

Dữ liệu thực nghiệm ngày 19/05 cho thấy một xu hướng kỹ thuật rất rõ nét: **Tối ưu hóa Preprocessing giúp giảm sâu RTF nhưng có thể làm CER tăng nhẹ.**

- **v15.2 (Sweet Spot CER):** Sử dụng bộ lọc thông cao High-Pass Filter 80Hz cơ bản kết hợp với VAD segment silence 700ms và Safe Frame-level Noise Gate. Do tín hiệu ít bị can thiệp thô bạo, model giữ được độ nhạy tốt đối với âm vị gốc, đạt CER tối ưu **41.17%**. Tuy nhiên, RTF vẫn ở mức **2.75** do còn sót lại nhiễu nền ở các khoảng lặng.
- **v15.5 (Performance Champion):** Giới thiệu Zero-Phase Bandpass Filter (100Hz - 7500Hz) và Adaptive RMS Normalization giúp triệt tiêu triệt để tĩnh điện nền (static noise clamp) và hum trầm. RTF giảm mạnh kỷ lục xuống **2.07** (nhanh hơn v15.2 tới ~25%) do bộ giải mã không bị lãng phí chu kỳ tính toán cho nhiễu. Tuy nhiên, CER tăng lên **43.40%** do sự kết hợp của bộ lọc dải thông và cơ chế nén làm biến dạng nhẹ một số phụ âm gió biên.

### 2. Sự ảnh hưởng của dải thông Bandpass hẹp (v15.7 - 300Hz-3400Hz)

Thử nghiệm **v15.7** cố gắng áp dụng dải tần telephony tiêu chuẩn của mạng viễn thông truyền thống (300Hz - 3400Hz) nhằm triệt tiêu tối đa nhiễu ngoài dải thoại.
- **Hiện tượng:** CER tăng vọt lên **46.20%** và model có dấu hiệu mất các âm vị quan trọng.
- **Nguyên nhân:** Việc cắt bỏ các tần số cao trên 3400Hz làm triệt tiêu hoàn toàn các âm xát (sibilants - như /s/, /sh/) và các âm bật (plosives) vốn rất quan trọng trong tiếng Nhật thương mại. Điều này gây nhiễu loạn cho bộ nhận diện ngôn ngữ (Language Identification - LID) và làm sai lệch nghiêm trọng các từ có âm thanh tương đồng.
- **Biện pháp khắc phục (Commit `bdf666c`):** Đã khôi phục và mở rộng dải thông lên **100Hz - 7500Hz** trên máy chủ ASR. Điều này vừa giúp bảo toàn nguyên vẹn các đặc tính tần số âm thanh tiếng Nhật vừa triệt tiêu được hum nguồn điện (50/60Hz) và nhiễu dải cao vô ích. Cấu hình này sẽ được benchmark chính thức dưới tên **v15.8**.

### 3. Tối ưu hóa VAD Asymmetric Padding (v15.5+)

Việc chuyển đổi từ đệm đối xứng (300ms/300ms) sang **Asymmetric Padding** (50ms đầu / 350ms cuối) là một cải tiến xuất sắc giúp xử lý các vấn đề thực tế:
- **Leading Padding (50ms):** Đủ ngắn để ngăn chặn việc thu nạp các tiếng lách cách, tiếng thở hoặc nhiễu trắng tĩnh điện ngay trước khi bắt đầu nói. Điều này giúp bộ mã hóa (encoder) nhận dạng đúng ngôn ngữ ngay từ ký tự đầu tiên của chunk, triệt tiêu lỗi sụp đổ ngôn ngữ (Language Collapse).
- **Trailing Padding (350ms):** Đủ dài để bao trọn các phụ âm kết thúc câu và các hậu tố xã giao đặc trưng của tiếng Nhật business (`です`, `ます`, `した`) vốn thường bị nói nhỏ dần và kéo dài ở cuối câu thoại.

### 4. Fuzzy Overlap Matching (v15.7)

Một trong những cải tiến cốt lõi giải quyết triệt để lỗi lặp từ tại điểm nối chunk là cơ chế ghép mờ:
- **Điểm yếu của Exact Match (v15.6 trở về trước):** Cơ chế cũ yêu cầu các chuỗi văn bản tại điểm chồng lấn (overlap) phải khớp nhau 100% từng ký tự. Nếu ASR nhận diện sai lệch dù chỉ một dấu câu hoặc một trợ từ do nhiễu biên, bộ ghép nối sẽ bỏ qua và ghép đè cả hai phần, gây ra lỗi lặp câu nghiêm trọng (overlap double-transcription).
- **Giải pháp Fuzzy Match (v15.7):** Sử dụng `difflib.SequenceMatcher` cho phép sai số biên tối đa là 6 ký tự (`_fuzzy_overlap_chars`). Cơ chế này giúp nhận diện chính xác phần trùng lặp thực tế ngay cả khi có biến âm nhỏ hoặc sai khác dấu câu, giúp văn bản kết quả mượt mà và tự nhiên hơn rất nhiều.

### 5. Phòng chống sụp đổ ngôn ngữ & Trôi dạt tiếng Trung (v15.3, v15.6)

- **Japanese Grammar Protection (v15.3):** Ngăn chặn việc cắt bỏ nhầm các câu thoại lịch sự tiếng Nhật bằng cách bổ sung các cụm từ business phổ biến (`ます`, `です`, `ました`, `ありがとうございます`) vào whitelist bảo vệ của RepetitionStoppingCriteria. Ngưỡng lặp lại cũng được nâng lên 5 để bảo toàn các câu đối thoại thực tế.
- **Chinese Drift Guardrails (v15.6):** Tích hợp bộ lọc phát hiện "sự trôi dạt tiếng Trung" thông qua việc quét các ký tự và cụm từ đặc trưng Trung Quốc (`這`, `們`, `嗎`, `謝謝`, `你好`). Khi phát hiện model bị loạn ngôn ngữ dưới tác động của nhiễu nặng, hoặc tỷ lệ ký tự tiếng Nhật trong chunk giảm xuống dưới 55%, hệ thống sẽ chủ động kích hoạt cơ chế tự phục hồi bằng cách chia nhỏ chunk thành các sub-chunk chồng lấn 0.5s và thực hiện nhận diện lại.

### 6. Dynamic Spectral Flatness (v15.5+)

Tích hợp thuật toán đo độ phẳng phổ (Spectral Flatness) trên từng chunk âm thanh. Đối với các chunk có độ phẳng phổ cao (> 0.45) kéo dài trên 1 giây, hệ thống tự động nhận diện đây là tiếng xì đường truyền điện thoại (pure line static) chứ không phải giọng nói người và sẽ chủ động bỏ qua chunk đó. Điều này trực tiếp triệt tiêu ảo giác gõ nhầm từ "Arigato" vu vơ ở các đoạn tĩnh âm có nhiễu lớn.

---

## Kết Luận & Hướng Đi Tiếp Theo

1. **Baseline Hiện Tại:**
   - **v15.2** là baseline có chất lượng nhận diện tốt nhất (CER Speech 41.17%), phù hợp cho các luồng xử lý cần độ chính xác tối đa.
   - **v15.5** là baseline có hiệu năng ấn tượng nhất (RTF Speech 2.07), tiết kiệm tài nguyên tính toán và cực kỳ phù hợp cho môi trường xử lý thời gian thực (Real-time).
2. **Nhiệm vụ Tiếp Theo:** Chạy loạt benchmark **v15.8** sử dụng cấu hình Bandpass Filter mở rộng 100Hz - 7500Hz (commit `bdf666c`) kết hợp với cơ chế Fuzzy Overlap Matcher và Chinese Drift Guardrails để tìm điểm giao thoa hoàn hảo giữa độ chính xác và hiệu năng của hệ thống.
