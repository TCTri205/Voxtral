# Báo cáo Phân tích Chuyên sâu: Lỗi Hallucination trên file `media_148414`

## 1. Tổng quan Vấn đề

- **File audio**: `media_148414_1767922241264 (1).mp3`
- **Hiện tượng**: Model `Voxtral-Mini-4B-Realtime-2602` trả về duy nhất một câu tiếng Anh: *"Hi, Joseph. I'm sorry."*, bỏ qua toàn bộ 48 giây nội dung hội thoại tiếng Nhật.
- **Tính chất**: Lỗi có tính deterministic cao (lặp lại 100% qua nhiều lần chạy).

---

## 2. Các Sự kiện Đã được Chứng minh (Proven Facts)

Dựa trên kết quả thực nghiệm tại `walkthrough_v2.md`:

1. **Điểm kích hoạt (Trigger Point)**: Lỗi đã được cô lập nằm trong 5 giây đầu tiên (`segment_00`). Khi chạy các đoạn từ giây thứ 5 trở đi một cách độc lập, model cho kết quả tiếng Nhật chính xác. Việc trim đầu file là một hướng xử lý thực tế cần được kiểm chứng thêm trên toàn bộ audio.
2. **Khóa ngôn ngữ (Language Lock-in)**: Model bị "kẹt" trong không gian xác suất tiếng Anh ngay từ những token đầu tiên. Việc tăng `temperature` (0.1 -> 0.7) chỉ làm tăng độ dài câu tiếng Anh (hallucination dài hơn) chứ không giúp model thoát sang tiếng Nhật.
3. **Yếu tố không ảnh hưởng (Non-factors)**:
    - **Prompt**: Thay đổi hoặc xóa bỏ prompt không làm thay đổi kết quả.
    - **Sample Rate**: Tất cả các file trong tập dữ liệu đều là 8kHz, và hầu hết vẫn được xử lý đúng. 8kHz không phải là nguyên nhân trực tiếp.

---

## 3. Suy luận Hợp lý (Reasonable Inferences)

1. **Cơ chế Tự hồi quy (Autoregressive)**: Một cơ chế hợp lý là tính tự hồi quy trong quá trình giải mã khiến các token ảo giác đầu tiên (tiếng Anh) đóng vai trò làm ngữ cảnh (context) ép các token sau phải tuân thủ logic ngôn ngữ đó.
2. **Kết thúc sớm**: Việc model sinh ra một câu hoàn chỉnh về mặt ngữ nghĩa ngay từ đầu có thể dẫn tới việc kết thúc giải mã sớm (có thể qua EOS hoặc cơ chế dừng tương đương), khiến phần âm thanh phía sau bị bỏ qua.

---

## 4. Giả thuyết / Cần kiểm chứng thêm (Hypotheses)

Các giả định dựa trên quan sát phổ âm thanh nhưng cần thực nghiệm thêm để khẳng định:

1. **Acoustic Pattern Trigger**: Giả thuyết rằng nhiễu trắng (noise), tiếng chuông (dial tone) hoặc âm thanh chuyển mạch viễn thông ở 1-2 giây đầu có đặc điểm họa âm (harmonics) trùng lặp ngẫu nhiên với các mẫu "greeting" trong tập dữ liệu huấn luyện.
2. **Ngưỡng EOS**: Chưa khẳng định chính xác model dừng do EOS chủ động hay do sự sụp đổ xác suất sau khi hoàn thành câu ảo giác.

---

## 5. Giải pháp Kỹ thuật Đề xuất (Optimized Solutions)

Thay vì kỳ vọng model tự sửa lỗi, hệ thống cần có cơ chế bọc (wrapper) để xử lý các case ngoại lệ này.

### Giải pháp 1: Retry với Cửa sổ Trượt (Trim Sweep)

Thay vì cố định cắt 5 giây, triển khai cơ chế **Shift/Trim Sweep**:

- Nếu phát hiện output nghi vấn (ngắn bất thường so với audio), thực hiện retry với các bước trượt nhỏ (VD: cắt 0.5s, 1s, 2s).
- Mục tiêu: Tìm điểm "sạch" để model bắt đúng ngôn ngữ mà không làm mất quá nhiều nội dung đầu.

### Giải pháp 2: Suy luận theo Chunk có Overlap (Chunked Inference)

Để tăng độ bền vững (robustness) cho production:

- Chia audio thành các chunk 15-20s.
- **Quan trọng**: Các chunk phải có độ chồng lấn (overlap ~2-3s) và logic ghép nối (stitching) dựa trên timestamp hoặc token overlap.
- Ưu điểm: Một chunk bị "văng" sang tiếng Anh sẽ không làm chết các chunk phía sau.

### Giải pháp 3: Cơ chế Fallback dựa trên Heuristics trung tính

Thiết lập lớp đánh giá kết quả (Evaluation Layer) để kích hoạt Retry:

- **Tỷ lệ Text/Length**: Nếu `tỷ lệ ký tự / giây âm thanh` quá thấp (VD < 1 ký tự/giây cho file > 10s).
- **Tỷ lệ ASCII/Non-ASCII**: Với hệ thống ưu tiên Tiếng Nhật, nếu kết quả trả về 100% ASCII trong khi mong đợi là CJK, đánh dấu là `SUSPICIOUS_HALLUCINATION`.
- **Confidence Proxy**: Theo dõi xác suất (logprobs) của các token đầu tiên.

---

> [!NOTE]
> Báo cáo này tách biệt rõ ràng giữa bằng chứng thực nghiệm và các suy luận kỹ thuật để phục vụ việc ra quyết định chính xác hơn.
