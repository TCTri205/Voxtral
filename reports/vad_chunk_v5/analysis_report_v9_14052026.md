# Báo cáo Phân tích Chuyên sâu Voxtral ASR - Phiên bản v9 (14/05/2026)

## 1. Tổng quan tình trạng (Executive Summary)
Kết quả Benchmark phiên bản **v9** cho thấy sự sụt giảm về độ chính xác và hiệu suất so với các phiên bản trước (v6). Mặc dù hệ thống đã miễn nhiễm hoàn toàn với nhiễu trắng (0.000 HRS), nhưng lại xuất hiện các loại lỗi mới nghiêm trọng hơn.

**Các chỉ số chính:**
- **Average CER:** **43.28%** (Tăng từ 40.27% ở v6).
- **Average RTF:** **3.595** (Cá biệt có file lên tới **9.38**).
- **Trạng thái:** **F (Fail)** cho 9/11 file test.

---

## 2. Phân tích các vấn đề nghiêm trọng (Critical Issues)

### 2.1. Ảo giác Đa ngôn ngữ (Multilingual Hallucinations)
Đây là lỗi nghiêm trọng nhất khiến CER tăng vọt và làm hỏng hoàn toàn nội dung transcript.
- **Hiện tượng:** Model sinh ra tiếng Nga (`Человек, может, это...`) hoặc các ký tự lạ không thuộc tiếng Nhật.
- **Ví dụ điển hình:** File `media_149291_1769069811005.mp3`.
- **Nguyên nhân kỹ thuật:** 
    - Hàm `_detect_language_collapse` hiện tại chỉ kiểm tra **ASCII Ratio** (dành cho tiếng Anh). Ký tự Cyrillic hoặc các ngôn ngữ khác không phải ASCII nên lưới lọc bị vô hiệu hóa.
    - Cơ chế retry không được kích hoạt vì hệ thống lầm tưởng đây là tiếng Nhật "hợp lệ" (ASCII ratio = 0).

### 2.2. Hiện tượng "Inference Stalling" (Đình trệ xử lý)
Hiệu suất xử lý bị kéo dài bất thường, ảnh hưởng đến khả năng đáp ứng thời gian thực.
- **Hiện tượng:** File `media_149291` tốn hơn **24 phút** để xử lý (RTF 9.38), với **292 keepalive** gửi đi.
- **Nguyên nhân kỹ thuật:** 
    - Model rơi vào trạng thái "unstable" do audio đầu vào không rõ ràng hoặc nhiễu, dẫn đến việc sinh tối đa token cho phép (`max_new_tokens=512`).
    - Cơ chế `RepetitionStoppingCriteria` chưa đủ nhạy để ngắt các vòng lặp ảo giác phức tạp (không lặp lại chính xác 100% ký tự).

### 2.3. Vấn đề VAD & Ngữ cảnh (Over-segmentation)
- **Hiện tượng:** File 156 giây bị chia nhỏ thành **40 segments** (trung bình ~3.9s/segment).
- **Hệ quả:** Việc chia quá nhỏ khiến model mất "trí nhớ ngắn hạn" về các câu trước đó, dẫn đến sai lệch thông tin thực thể:
    - **Số điện thoại:** `050` bị nghe thành `デロコーゼロ` (lỗi ngữ âm nghiêm trọng).
    - **Tên riêng:** `梅田` (Umeda) → `メイド` (Maid), `返信` (Reply) → `弊社` (Our company).

---

## 3. Nguyên nhân gốc rễ (Root Causes)

1. **Lỗ hổng trong Logic Guardrail:** Cơ chế phát hiện Language Collapse quá hẹp, chỉ tập trung vào tiếng Anh/ASCII.
2. **Cấu hình VAD chưa tối ưu cho Telephony:** `VAD_SEGMENT_SILENCE_MS = 700ms` là quá ngắn cho các cuộc hội thoại điện thoại có nhiều quãng nghỉ tự nhiên, gây nát câu (over-segmentation).
3. **Model Bias:** Model 4B có xu hướng "tự điền" (over-guessing) các cụm từ chào hỏi phổ biến trong kinh doanh Nhật Bản khi tín hiệu âm thanh yếu.

---

## 4. Đề xuất Kế hoạch Hành động (Action Plan)

| Nhiệm vụ | Giải pháp kỹ thuật | Ưu tiên |
| :--- | :--- | :--- |
| **Sửa lỗi ảo giác Nga** | Nâng cấp `_detect_language_collapse` để kiểm tra tỷ lệ ký tự tiếng Nhật thực tế thay vì chỉ loại trừ ASCII. | **Cao** |
| **Chống Stalling** | Thêm `max_time_per_chunk` guardrail và siết chặt stopping criteria cho n-gram dài (n>=5). | **Cao** |
| **Gộp câu VAD** | Tăng `VAD_SEGMENT_SILENCE_MS` lên **1000ms - 1200ms** để duy trì ngữ cảnh tốt hơn. | Trung bình |
| **Lọc nhiễu Telephony** | Áp dụng bộ lọc Band-pass (300Hz-3.4kHz) trong tiền xử lý để làm sạch đặc thù giọng nói qua điện thoại. | Trung bình |

---
**Người báo cáo:** Antigravity (AI Assistant)
**Dựa trên kết quả run:** `results\14-05-2026_v9`
