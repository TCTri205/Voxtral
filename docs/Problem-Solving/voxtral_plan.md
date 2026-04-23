# Voxtral ASR Pipeline Optimization — Implementation Plan (Colab T4 / Transformers)

## Mục tiêu

Khắc phục 3 vấn đề nghiêm trọng nhất trên môi trường Google Colab (GPU T4) qua các cấu hình thực tế code hiện đang thiếu:

1. **Language Collapse** → Ép giải mã tiếng Nhật triệt để (do `voxtral_server_transformers.py` hiện tại không truyền language hint).
2. **Insertion Hallucinations** → Lọc bỏ nhiễu/khoảng lặng ngay trước khi gọi model (`model.generate`) bằng Silero VAD.
3. **Realtime Output (Streaming)** → Sử dụng `TextIteratorStreamer` để yield kết quả ngay lập tức thay vì chặn đợi toàn bộ âm thanh (để fix ngắt lời sớm và giảm độ trễ thực tế).

---

## Cấu hình Môi trường Tối ưu (Google Colab T4)

* **GPU:** Tesla T4 (16GB VRAM).
* **Kiểu dữ liệu:** `torch.float16` (Bắt buộc vì T4 không hỗ trợ native `bfloat16`).
* **Thư viện:** `transformers >= 5.2.0`, `silero-vad` (từ torch hub), `librosa`.

---

## Các Giai đoạn Triển khai (Đã được điều chỉnh sau code review)

### Phase 1: VAD Gatekeeper để chống Hallucinations (Dễ nhất, Hiệu quả cao nhất)

**Vấn đề:** Model gặp file trắng hoặc nhiễu sẽ sinh ra văn bản rác lặp lại không hồi kết.
**Triển khai:**

1. Trong `voxtral_server_transformers.py`, tải Silero VAD lúc khởi tạo:
   `vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')`
2. Tại event `input_audio_buffer.commit`, chia buffer âm thanh thành các chunk 512 mẫu (hoặc gửi cả cụm vào VAD threshold logic).
3. Nếu xác suất tiếng nói trung bình `< 0.3` (hoặc không có khung nào vượt cửa sổ 0.5), ta bỏ qua việc chặn thread và gửi thẳng WebSocket `<empty_transcript>`.

### Phase 2: Tokenizer Language Hint

**Vấn đề:** Model nhận `audio_array` thuần túy, hay rơi vào tiếng Anh.
**Triển khai:**

1. Sử dụng kỹ thuật Prompt Injection: Tiêm tiền tố đặc biệt báo hiệu tiếng Nhật (VD: chuẩn token `TranscriptionRequest` hoặc prefix IDs của `AutoProcessor`). Chỉnh sửa hàm `_run_inference_sync` để đưa token IDs ngôn ngữ tiếng Nhật ghép trực tiếp vào trước quá trình model decode.

### Phase 3: Realtime Token Streamer (Khắc phục chờ quá lâu)

**Vấn đề:** `voxtral_server_transformers.py` và `run_asr.py` dùng vòng lặp chờ (`await asyncio.sleep(5)` keepalive) tới tút khi ra transcript cuối cùng.
**Triển khai (Server):**

1. Khởi tạo `streamer = TextIteratorStreamer(processor.tokenizer, skip_special_tokens=True)`.
2. Truyền `streamer=streamer` vào `model.generate()`. Gọi `model.generate()` bằng `threading.Thread`.
3. Vòng lặp lấy `for text in streamer:` sẽ gọi callback async thông báo ngược lại WebSocket bằng type `response.audio_transcript.delta`.
**Triển khai (Client):**
4. Sửa `run_asr.py` để lắng nghe event `type == 'response.audio_transcript.delta'`, lấy field `delta` và in trực tiếp ra màn hình `print(token, end="")`.

---

## Các Phương án Đã Loại bỏ (Không Khả thi)

*Ghi chú: Giữ lại để tham khảo và tránh lỗi lặp lại trong tương lai.*

1. **Sử dụng API `language="ja"` trong TranscriptionRequest ảo tưởng trên config:**
    * *Nguyên nhân:* Bị hệ thống bỏ qua ở lớp tensor do kiến trúc Streaming chưa bắt token này, ta phải inject token IDs bằng tay.
2. **Chiến lược Phân mảnh thủ công (Manual Chunking & Overlapping):**
    * *Nguyên nhân:* Phá vỡ lợi thế của kiến trúc mã hóa nhân quả, tăng 5 lần chi phí GPU.
3. **Fallback Temperature = 0.2 khi gặp ký tự lặp:**
    * *Nguyên nhân:* Có thể làm hỏng trạng thái token.

---

## Kế hoạch Xác minh (Verification Plan)

### Kiểm tra Tự động

* Sử dụng `run_asr.py --audio audio/silence_60s.wav` -> Chắc chắn không có rác, VAD phải catch được và trả rỗng lập tức.
* Thử file `audio/ja_test_noisy.wav` -> Phải trả về tiếng Nhật nhờ tokenizer hint (không bị fall về tiếng Anh).
* Quan sát trên console, với `run_asr.py`, khi xử lý, text phải chảy ra từ từ trên console (delta streams).
