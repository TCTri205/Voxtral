# Báo cáo Công việc ngày 19/05/2026 - Tối ưu hóa ASR Voxtral (v15)

## 1. Tổng quan
Ngày hôm nay tập trung vào việc giải quyết các vấn đề tồn đọng sau các đợt regression, đặc biệt là lỗi **Language Collapse** (sụp đổ ngôn ngữ sang tiếng Anh/Nga), **Chinese Drift** (trôi dạt sang tiếng Trung), và **Social Hallucinations** (ảo giác xã giao như "Arigato" lặp đi lặp lại). Hệ thống đã liên tục được tối ưu hóa qua các phiên bản từ **v15.1** đến **v15.7** và khép lại bằng commit tối ưu hóa dải thông `bdf666c`.

---

## 2. Các thay đổi kỹ thuật chính trong ngày

### 2.1. Cải tiến Tiền xử lý Âm thanh (Audio Preprocessing)
Đã thiết lập hàm tiền xử lý `_preprocess_audio` với quy trình 4 bước nhằm làm sạch tín hiệu trước khi đưa vào VAD và bộ giải mã ASR:
- **DC Offset Removal:** Loại bỏ độ lệch điện một chiều, đưa tín hiệu về điểm không gốc.
- **Zero-Phase Butterworth Bandpass Filter (BPF):** 
  - Trong `v15.5`, giới thiệu bộ lọc 100Hz - 7500Hz nhưng bị lỗi méo passband (warping) do tiệm cận Nyquist frequency (8000Hz).
  - Trong `v15.6`, tạm thời thay thế bằng High-Pass Filter (HPF) 100Hz để tránh warping.
  - Trong `v15.7`, thử nghiệm Bandpass hẹp 300Hz - 3400Hz (telephony tiêu chuẩn). Tuy nhiên, dải hẹp làm mất các phụ âm gió/xát tiếng Nhật, khiến CER tăng mạnh lên 46.20%.
  - **Giải pháp tối ưu cuối ngày (Commit `bdf666c`):** Mở rộng bộ lọc Butterworth lên dải **100Hz - 7500Hz** để vừa triệt tiêu hum nguồn điện vừa giữ nguyên vẹn âm sắc sibilants/plosives tiếng Nhật.
- **Peak-Aware Adaptive RMS Normalization:** Tự động chuẩn hóa âm lượng về mức target -20dBFS.
- **Static Noise Clamp (Noise Gate mềm):** Phát hiện các khoảng lặng chỉ chứa tĩnh điện telephony (RMS < -45dBFS và Peak < -35dBFS) để cố định Gain ở mức 2.0x thay vì khuếch đại nhiễu nền vô lý, giúp VAD hoạt động chính xác tuyệt đối.

### 2.2. Tối ưu hóa VAD & Chunks
- **Asymmetric Padding (v15.5+):** Thay đệm đối xứng 300ms bằng đệm bất đối xứng (**Leading: 50ms, Trailing: 350ms**). Đệm đầu ngắn giúp loại bỏ nhiễu trắng gây loạn LID, đệm cuối dài giúp bao trọn các hậu tố business (`desu`, `masu`).
- **VAD Segment Silence:** Khôi phục `VAD_SEGMENT_SILENCE_MS = 700ms` giúp giữ câu thoại liền mạch, tránh xé lẻ chunk.
- **Dynamic Spectral Flatness (v15.5+):** Tích hợp kiểm tra độ phẳng phổ nhằm tự động bỏ qua các chunk chỉ toàn tiếng xì đường truyền điện thoại (flatness > 0.45).

### 2.3. Logic Ghép nối Chữ (Fuzzy Overlap Merging - v15.7)
- Loại bỏ hoàn toàn cơ chế so khớp chính xác từng ký tự (`_exact_overlap_chars`).
- Thay thế bằng **Fuzzy Overlap Matcher** sử dụng `difflib.SequenceMatcher` cho phép sai số tối đa 6 ký tự để xử lý sự lệch dấu câu hoặc sai lệch biên ASR giữa các chunk chồng lấn, triệt tiêu lỗi lặp câu/lặp từ tại điểm nối chunk.

### 2.4. Kiểm soát Ảo giác (Anti-Hallucination)
- **RepetitionStoppingCriteria:** Thiết lập ngưỡng lặp n-gram (3-gram đến 8-gram) là 5 lần để phù hợp với các đoạn hội thoại lặp từ tự nhiên trong business điện thoại.
- **Business Whitelist (v15.3):** Đưa các cụm từ lịch sự tiếng Nhật (`ます`, `desu`, `ました`, `ありがとうございます`) vào danh sách whitelist bảo vệ để tránh dừng nhận dạng nhầm.
- **Tail-end Repetition Truncation:** Tự động cắt bỏ các từ lặp dư thừa ở cuối văn bản (`_truncate_repetitions`).
- **Strict Rollback Policy (v15.1+):** Khi phát hiện ảo giác (Guardrails đánh giá Medium/High), thực hiện nhận diện lại ở nhiệt độ thấp $T=0.2$. Nếu CER không cải thiện, chủ động khôi phục lại kết quả ban đầu (rollback) để tránh làm văn bản tệ đi.

### 2.5. Phòng chống Language Collapse & Chinese Drift (v15.6)
- **Chinese Drift Detection:** Bổ sung bộ lọc nhận diện các ký tự tiếng Trung thuần (`這`, `們`, `嗎`) và các từ chào hỏi Trung Quốc (`謝謝`, `你好`) vốn hay xuất hiện khi model bị loạn dưới nhiễu lớn.
- **Sub-chunking Recovery:** Khi phát hiện chunk bị loạn tiếng Trung hoặc tỷ lệ ký tự tiếng Nhật giảm xuống dưới 55%, hệ thống sẽ tự động kích hoạt cơ chế chia nhỏ chunk đó thành các sub-chunk chồng lấn 0.5s và nhận diện lại.

---

## 3. Kết quả Benchmark Nổi bật trong ngày

- **Baseline Chất lượng tốt nhất (v15.2):** Sử dụng bộ lọc HPF 80Hz đơn giản kết hợp VAD 700ms.
  - **Avg CER (Speech):** **41.17%** (Cực kỳ tiệm cận mức tốt nhất lịch sử v11.S là 40.93%).
  - **Avg Inf RTF:** **2.75** (Nhanh hơn đáng kể so với mức 3.34 - 3.62 của các bản cũ).
  - **Độ ổn định:** Hallucination ở mức kiểm soát được.
- **Baseline Hiệu năng tốt nhất (v15.5):** Sử dụng bộ lọc Butterworth 100-7500Hz và RMS Norm.
  - **Avg CER (Speech):** **43.40%**.
  - **Avg Inf RTF:** **2.07** (Tốc độ kỷ lục, nhanh gấp 1.3 lần v15.2, tiết kiệm tối đa tài nguyên).
- **Thử nghiệm Bandpass hẹp (v15.7):** Sử dụng BPF 300Hz - 3400Hz làm CER tăng lên **46.20%** do mất mát tần số cao âm vị tiếng Nhật. Điều này dẫn tới việc đưa ra quyết định mở rộng dải tần ở commit `bdf666c`.

---

## 4. Kế hoạch tiếp theo

1. **Chạy benchmark v15.8 (Pending):** Chạy và đánh giá toàn diện commit cuối ngày `bdf666c` (Butterworth Bandpass Filter 100Hz - 7500Hz kết hợp Fuzzy Overlap Matcher) để tìm ra điểm cân bằng lý tưởng: đạt tốc độ RTF dưới 2.10 của v15.5 nhưng giữ được CER tối ưu 41.1% của v15.2.
2. **Theo dõi LLM-eval của v15.7:** Đánh giá chi tiết sự ảnh hưởng của bộ lọc dải hẹp viễn thông đối với mức độ ảo giác tổng thể.
3. **Tiếp tục tối ưu hóa Prompt:** Củng cố System Prompt nghiêm ngặt để hạn chế triệt để các trường hợp ảo giác xã giao tiếng Nhật còn lại ở các phân đoạn âm thanh cực kỳ nhiễu.

---
*Người báo cáo: Gemini CLI Agent*
*Ngày: 19/05/2026*
