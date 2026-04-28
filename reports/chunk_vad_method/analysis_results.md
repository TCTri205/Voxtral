# Phân tích chi tiết kết quả ASR Voxtral (Run: 28-04-2026_v1)

Sau khi đối chiếu kỹ giữa [results.json](file:///D:/VJ/Voxtral/results/28-04-2026_v1/results.json), [ground_truth.json](file:///D:/VJ/Voxtral/ground_truth.json) và logs hệ thống, tôi đã tổng hợp báo cáo hoàn chỉnh về các vấn đề hiện tại của hệ thống.

## 1. Độ chính xác & Chất lượng nhận dạng (Average CER: 37.13%)

Tỷ lệ lỗi hiện tại rất cao, chủ yếu do 3 nhóm nguyên nhân kỹ thuật sau:

- **Hiện tượng Hallucination tiếng Anh:**
  - Trong các file dài (như `media_148954`, `media_149291`), model xuất hiện các câu tiếng Anh hoàn toàn không có trong audio (vd: *"Now, how does someone communicate..."*, *"So this call. Just to ask that."*).
  - **Nguyên nhân:** Model có thể bị ảnh hưởng bởi nhiễu hoặc khoảng lặng giữa các chunk, dẫn đến việc tự "sáng tác" nội dung thường thấy trong bộ dữ liệu training.
- **Mất đoạn nội dung (Segment Loss):**
  - Điển hình tại file `media_148284_...` (audio 40s nhưng transcript chỉ có đoạn đầu).
  - **Nguyên nhân:** Cơ chế VAD (nhận diện giọng nói) có thể đã phân loại nhầm các chunk tiếp theo là im lặng và bỏ qua không xử lý (skipping inference).
- **Nhạy cảm Kanji/Kana:**
  - Sự sai lệch giữa cách viết (辻 vs ツジ) đóng góp đáng kể vào CER dù nội dung âm thanh đúng. Hệ thống cần một bộ chuẩn hóa (Normalization) mạnh hơn trước khi đánh giá.

## 2. Vấn đề về Cơ chế Chunking & Merging

Hệ thống hiện tại đang sử dụng cơ chế chia nhỏ audio (15s/chunk) và ghép nối thô (Simple Concatenation):

- **Lỗi lặp từ tại điểm nối:** Với 1s overlap, việc ghép nối bằng cách cộng chuỗi đơn thuần dễ dẫn đến lặp lại các câu/từ nằm ở biên của 2 chunk.
- **Giới hạn Max Tokens:** Việc giới hạn `max_new_tokens=512` cho mỗi chunk 15s có thể là quá thấp nếu hội thoại diễn ra nhanh và dày đặc, dẫn đến việc transcript bị cắt cụt giữa chừng.

## 3. Hiệu năng hệ thống (RTF: 2.15)

- **Tốc độ xử lý:** RTF > 2.0 là mức chậm (xử lý lâu hơn 2 lần thời gian thực).
- **Cảnh báo Keepalive:** Số lượng keepalive cao trong logs cho thấy server đang bị nghẽn (bottleneck) tại bước Inference, khiến client phải đợi lâu sau khi đã gửi lệnh commit.

## Đề xuất cải thiện hoàn chỉnh

1. **Nâng cấp cơ chế Merging:** Thay vì cộng chuỗi đơn thuần, cần sử dụng thuật toán tìm điểm khớp (Sequence Matching) để khử trùng lặp tại các đoạn audio overlap (1s).
2. **Điều chỉnh VAD:** Giảm độ nhạy hoặc thêm padding lớn hơn để tránh việc VAD bỏ sót các đoạn hội thoại có âm lượng nhỏ.
3. **Hallucination Guardrails:** Kích hoạt hoặc tinh chỉnh cơ chế `VOXTRAL_RETRY_HALLUCINATION` để phát hiện và chạy lại các đoạn có dấu hiệu "sáng tác" tiếng Anh.
4. **Chuẩn hóa dữ liệu đánh giá:** Thực hiện một bước chuẩn hóa Kanji -> Kana hoặc loại bỏ các chú thích không cần thiết trong Ground Truth để có con số CER phản ánh đúng thực tế năng lực của model hơn.

**Kết luận:** Hệ thống đã chạy thông suốt về mặt quy trình (Pipeline), nhưng cần tối ưu mạnh về thuật toán ghép nối và cấu hình Inference để có thể ứng dụng thực tế.
