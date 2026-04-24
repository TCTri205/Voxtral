# Bản Phân Tích & Kế Hoạch Triển Khai Hoàn Chỉnh (Voxtral ASR)

Tài liệu này là bản chốt lại sau khi đối chiếu trực tiếp với mã nguồn hiện tại của:

- `voxtral_server_transformers.py`
- `run_asr.py`

Mục tiêu là giữ đúng những gì đã được xác thực, loại bỏ các giả định chưa có bằng chứng, và chuyển kế hoạch sang dạng đủ rõ để triển khai mà không phải tự đoán thêm hành vi.

---

## I. Đánh Giá Thực Trạng

### 1. Language Collapse

- Server hiện dùng text priming tại bước tạo `processor(...)` với prompt tiếng Nhật `日本語で書き起こしてください。`.
- Cơ chế này là **soft bias**, không phải hard language lock.
- Từ bằng chứng hiện có trong repo, **chưa có cơ sở chắc chắn** rằng `Voxtral-Mini-4B-Realtime-2602` hỗ trợ language forcing kiểu `forced_decoder_ids`, `lang_to_id`, hoặc cơ chế inject token tương đương Whisper trong luồng realtime hiện tại.

**Kết luận**

- Giữ nguyên text priming hiện tại.
- Không triển khai token injection hoặc hard language forcing ở vòng này.
- Nếu cần cải thiện độ ổn định tiếng Nhật, chỉ thử nghiệm các thay đổi nhỏ, ít rủi ro:
  - điều chỉnh nội dung prompt priming,
  - thử tăng độ nhấn của prompt,
  - giữ `temperature = 0.0`.

### 2. Latency do Commit-time VAD

- Server hiện chỉ chạy Silero VAD khi nhận `input_audio_buffer.commit`.
- Điều này có nghĩa là VAD đang quét **toàn bộ buffer** đã tích lũy, nên thời gian xử lý tăng theo độ dài audio/silence buffer.
- Đây là nút thắt latency thực sự của hệ thống hiện tại.

**Kết luận**

- Cần thêm incremental VAD để giảm khối lượng xử lý vô ích trước lúc infer.
- Tuy nhiên, với protocol hiện tại, client vẫn gửi toàn bộ audio rồi mới `commit`, nên incremental VAD **không thể** tự nó làm cho file `silence_60s.wav` trả `done` gần như tức thời nếu client vẫn stream đủ 60 giây trước khi commit.
- Vì vậy, mục tiêu thực tế của vòng này là:
  - giảm chi phí VAD ở thời điểm `commit`,
  - tránh đưa buffer hoàn toàn im lặng vào inference,
  - chuẩn bị nền cho realtime segmentation về sau.

### 3. Transcript Mismatch ở Client

- Client hiện in `delta` ra console ngay khi nhận được.
- Khi server gửi `response.audio_transcript.done`, client chỉ in `final_transcript` nếu trước đó chưa nhận được delta nào.
- Kết quả là:
  - người dùng có thể nhìn thấy một bản transcript thô trên console,
  - trong khi dữ liệu cuối cùng lưu vào kết quả lại là bản transcript khác.

**Kết luận**

- Đây là lỗi UX/debug thực sự.
- Cần thống nhất hiển thị cuối cùng theo `final_transcript`.

### 4. Minor Issues đã xác thực

- `duration = 0` khi dùng `--server-audio-dir` làm metric `RTF` bị sai hoặc vô nghĩa.
- `transcription_delay_ms` hiện được client gửi lên nhưng server không dùng vào bất kỳ logic runtime nào.

---

## II. Kế Hoạch Triển Khai

### Ưu tiên 1: Incremental VAD an toàn, không đổi protocol

**Mục tiêu**

- Giảm chi phí xử lý silence.
- Không thay đổi semantics hiện tại của luồng `append -> commit -> done`.
- Không auto-clear toàn bộ buffer trước `commit`.

**Phạm vi sửa**

- Chỉnh `voxtral_server_transformers.py`.

**Thiết kế chốt**

- Giữ inference chỉ chạy khi nhận `input_audio_buffer.commit`.
- Bổ sung trạng thái VAD theo connection trong lúc nhận `input_audio_buffer.append`.
- Mỗi lần append:
  - chỉ phân tích một cửa sổ ngắn gần cuối buffer, ví dụ 1-2 giây,
  - cập nhật các cờ nhẹ như `speech_seen` hoặc `recent_silence_only`,
  - không gọi inference,
  - không gửi transcript sớm,
  - không xóa trắng toàn bộ `audio_buffer`.
- Khi `commit`:
  - nếu toàn bộ session chưa từng thấy speech đáng kể, trả transcript rỗng ngay và bỏ qua inference,
  - nếu đã thấy speech, tiếp tục luồng hiện tại.

**Ràng buộc bắt buộc**

- Không được làm mất audio chỉ vì người dùng có pause ngắn giữa câu.
- Không được tự động trả `done` trước khi có `commit` trong vòng này.
- Nếu cần trimming, chỉ được cân nhắc cắt **silence đầu buffer đã được xác nhận ổn định**, không được cắt phần speech hoặc khoảng ngắt ngắn chưa đủ chắc chắn.

### Ưu tiên 2: Đồng bộ transcript hiển thị với transcript cuối

**Mục tiêu**

- Console phải phản ánh rõ transcript cuối cùng mà hệ thống ghi nhận.

**Phạm vi sửa**

- Chỉnh `run_asr.py`.

**Thiết kế chốt**

- Vẫn in `delta` theo thời gian thực như hiện tại.
- Khi nhận `response.audio_transcript.done`:
  - luôn lấy `final_transcript` làm kết quả chuẩn,
  - nếu trước đó chưa có delta, in `final_transcript` như hiện tại,
  - nếu đã có delta và `final_transcript` khác nội dung đã tích lũy, in thêm một dòng rõ ràng theo dạng `Final transcript: ...`,
  - nếu giống nhau, chỉ kết thúc dòng hiện tại bằng newline.

**Yêu cầu**

- Không cố “vẽ lại” cùng một dòng console bằng control sequence.
- Ưu tiên output rõ ràng, dễ debug, ít phụ thuộc terminal.

### Ưu tiên 3: Sửa metric và dọn API no-op

**Mục tiêu**

- Tránh sinh metric sai.
- Làm rõ tham số nào thực sự có tác dụng.

**Phạm vi sửa**

- Chỉnh `run_asr.py`.
- Có thể chỉnh nhỏ `voxtral_server_transformers.py` nếu cần làm rõ log hoặc bỏ tham số no-op.

**Thiết kế chốt**

- Nếu không xác định được `duration`, đặt các metric phụ thuộc duration thành `None` hoặc `"N/A"` ở tầng hiển thị, không trả `0` giả.
- Không dùng `0` để biểu diễn “không tính được”.
- Với `transcription_delay_ms`, chọn một trong hai hướng:
  - nếu chưa dùng ở runtime trong vòng này, giữ field để tương thích nhưng ghi rõ trong code/comment/log rằng nó chưa có hiệu lực,
  - không triển khai logic mới cho field này trong vòng sửa hiện tại.

### Không làm trong vòng này

- Không rewrite language forcing sang token injection.
- Không thay đổi protocol websocket để server chủ động `done` trước `commit`.
- Không biến incremental VAD thành auto-segmentation hoàn chỉnh.

---

## III. Verification Plan

### 1. Silence path

**Lệnh**

```bash
python run_asr.py --audio audio/silence_60s.wav --chunk-interval 0
```

**Kỳ vọng**

- Server bỏ qua inference.
- Transcript trả về rỗng.
- Thời gian xử lý sau `commit` giảm đáng kể so với cơ chế quét full-buffer rồi infer.

**Lưu ý**

- Dùng `--chunk-interval 0` để đo throughput/server behavior.
- Nếu dùng `--chunk-interval 0.1`, tổng thời gian end-to-end vẫn gần bằng thời lượng file do client chủ động giả lập realtime trước khi `commit`.

### 2. Streaming transcript consistency

**Lệnh**

```bash
python run_asr.py --audio audio/sample_japanese.wav --chunk-interval 0.1
```

**Kỳ vọng**

- Delta vẫn xuất hiện dần trên console.
- Khi nhận `done`, nếu transcript cuối khác transcript tích lũy từ delta, client in thêm dòng `Final transcript: ...`.
- File kết quả và thông tin hiển thị cho người dùng không còn mâu thuẫn ngầm.

### 3. Server-side audio metrics

**Lệnh**

```bash
python run_asr.py --audio_dir audio --server-audio-dir /content/Voxtral/audio --chunk-interval 0
```

**Kỳ vọng**

- Không còn `total_rtf = 0` hoặc `inference_rtf = 0` chỉ vì thiếu duration local.
- Kết quả hiển thị metric theo dạng `None` hoặc `N/A` khi không tính được.

---

## IV. Kết Luận Chốt

- Giữ nguyên **text priming** và không đụng vào hard language forcing trong vòng này.
- Tập trung vào ba việc có bằng chứng rõ ràng và lợi ích trực tiếp:
  - incremental VAD theo hướng an toàn, không đổi protocol,
  - đồng bộ transcript cuối ở client,
  - sửa metric duration/RTF và làm rõ `transcription_delay_ms` hiện là no-op.

Đây là phạm vi nhỏ nhất nhưng đủ để cải thiện độ tin cậy của benchmark, UX debug, và latency phía server mà không mở thêm rủi ro kiến trúc không cần thiết.
