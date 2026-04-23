# Phân tích & Đề xuất Cải thiện Chuyên sâu: Nhận diện sai ngôn ngữ (Language Collapse) & Ngắt lời sớm (Early Truncation)

Tài liệu này tập trung nghiên cứu cơ chế gốc rễ (root cause mechanism) của 2 vấn đề nghiêm trọng nhất gây ra CER 100% trong hệ thống Voxtral, đồng thời đề xuất các phương án kỹ thuật cụ thể (áp dụng cấp độ mã nguồn) để khắc phục triệt để.

---

## Phần 1: Nhận diện sai ngôn ngữ (Language Collapse)

### 1.1 Cơ chế gây lỗi (Root Cause Mechanism)

Các mô hình ASR kiến trúc LLM (như Whisper, Voxtral) sử dụng **Language Tokens** ở đầu sequence để quyết định tokenizer và bộ trọng số ngữ nghĩa để giải mã khúc âm thanh tiếp theo (ví dụ: `<|startoftranscript|><|ja|><|transcribe|>`).

**Quy trình thất bại trên Voxtral:**

1. **Thiếu định hướng:** Hệ thống đang chạy ở chế độ **Auto-detect Language** (bắt mô hình tự nghe 30 giây đầu và phỏng đoán).
2. **Audio bị nhiễu/Narrowband:** Khi gặp các file băng thông hẹp (rolloff ~2kHz) hoặc microphone rè, tín hiệu phổ (spectrogram) của tiếng Nhật bị mất các nét đặc trưng (đặc biệt là âm xát).
3. **Fallback Bias:** Mô hình mất tự tin vào kết quả phân tích âm thanh, và rơi vào "vùng an toàn" (Prior Bias). Vì tiếng Anh chiếm tỷ trọng lớn nhất trong dữ liệu huấn luyện của mọi mô hình foundation, Voxtral tự động đoán đây là tiếng Anh xen lẫn tiếng ồn → Xuất ra `<|en|>` và cố gắng dịch nhiễu thành các câu tiếng Anh thông dụng (VD: `"Hi, Joseph. I'm sorry."` trên file `media_148414`).

*(So sánh: Javis không bị lỗi này vì đã sử dụng lệnh ép cứng ngôn ngữ `language: "ja"` trong API request).*

### 1.2 Đề xuất giải pháp kỹ thuật

#### 🔴 Phương án 1A: Mồi Context Ngôn ngữ tại lớp Processor (Ưu tiên Cao nhất)

**Do hệ thống Voxtral phục vụ thị trường Nhật Bản**, việc cho phép mô hình phỏng đoán ngôn ngữ là một sự lãng phí rủi ro. Với kiến trúc `Voxtral-Mini-4B` (không dùng `forced_decoder_ids` của Whisper), ta có thể ép ngôn ngữ thông qua Text Prompting vào thẳng lớp `processor`.

- **Thực thi:** Sửa đổi file `voxtral_server_transformers.py` trong hàm `_run_inference_sync`.
- **Code mẫu:**

  ```python
  # Khởi tạo context sạch, bao gồm Token Tiếng Nhật hoặc Prompt tiếng Nhật
  # Điều này giúp khóa decoder vào không gian ngôn ngữ Nhật Bản ngay từ đầu
  inputs = processor(text="[Tiếng Nhật] ", audio=audio_obj.audio_array, return_tensors="pt")
  ```

- **Trade-off:** Nhanh gọn, giải quyết triệt để bệnh Language Collapse cho khách hàng Nhật. Không dùng được nếu có cuộc gọi tiếng Việt/Anh thuần túy.

#### 🟡 Phương án 1B: Prefix Prompting (Biasing Ngữ cảnh)

Đây là phương án mồi (warm-up) context window của decoder, hướng nó vào tiếng Nhật mà không tắt hẳn khả năng nhận tiếng Anh ở mức hệ thống.

- **Thực thi:** Truyền tham số `initial_prompt` (trong Whisper-like models, tham số này được gán vào đầu token sequence trước đoạn text).
- **Code mẫu:** Sử dụng một câu tiếng Nhật đặc trưng của domain.

  ```python
  initial_prompt = "以下は日本語の電話会話のコールセンターの音声認識結果です。よろしくお願いします。"
  ```

- **Trade-off:** Rất tốt cho các từ vay mượn (Katakana), sửa lỗi chính tả domain, nhưng hiệu lực ép ngôn ngữ yếu hơn Phương án 1A.

#### 🟢 Phương án 1C: Sử dụng Node LID (Language ID) Độc lập

**Dành cho hệ thống Multi-domain** (Yêu cầu nhận dạng cả tiếng Anh, Nhật, Hàn... nhưng audio quá nhiễu).

- **Thực thi:** Thêm một mạng Neural tí hon chuyên nhận diện ngôn ngữ (như `speechbrain/lang-id` - chỉ ~10MB) vào đầu pipeline. Nó sẽ "nghe" audio trước, ra quyết định (VD: 98% JA), sau đó truyền biến `language="ja"` vào hàm generate của Voxtral.
- **Trade-off:** Xử lý triệt để nhưng mất cấu trúc code hiện tại (thêm 1 step xử lý). Tăng độ trễ ~50-100ms.

---

## Phần 2: Ngắt lời sớm (Early Truncation)

### 2.1 Cơ chế gây lỗi (Root Cause Mechanism)

Lỗi này thường xảy ra trên các file rác hoặc file hội thoại rất dài (VD: `media_149291` kéo dài 156.7s).

**Quy trình thất bại trên Voxtral:**

1. **Window Size Logic:** Voxtral/Whisper có window xử lý tối đa thường là **30 giây**. Đối với file dài, hệ thống phải chạy cơ chế "Long-Form Transcription" — trượt cửa sổ n giây dựa trên timestamp của từ cuối cùng nhận diện được.
2. **"Bỏ cuộc" do nhiễu:** Khi cửa sổ hiện tại trượt trúng một đoạn khoảng lặng dài hoặc tạp âm (quạt, gõ phím), mô hình tính toán log-probability của toàn bộ đoạn đó.
3. Nếu xác suất rỗng cao (`no_speech_prob` > ngưỡng), mô hình sẽ xuất ra token `<|endoftext|>` thay vì trượt tiếp, gây "ngắt mạch" toàn bộ file âm thanh dù phía sau (phút thứ 2, phút thứ 3) vẫn còn tiếng người.

### 2.2 Đề xuất giải pháp kỹ thuật

#### 🔴 Phương án 2A: VAD-Guided Processing (Giải pháp Triệt để nhất)

Sử dụng Voice Activity Detection (VAD) để cắt bỏ hoàn toàn các khúc lặng/nhiễu ra khỏi audio trước khi đưa vào Voxtral.

- **Cơ chế:** Thay vì đưa file 156s nguyên khối vào Voxtral, VAD (ví dụ: `silero-vad`) sẽ băm file thành mảng: `[Segment(0.0-4.5s), Segment(7.2-12.0s), ...]`. Ta nạp từng segment nhỏ (<15s) vào mô hình.
- **Lợi ích kép:** Mô hình không bao giờ phải xử lý "khoảng trống" $\rightarrow$ không bao giờ bị kích hoạt cơ chế `no_speech_prob` $\rightarrow$ không bao giờ bỏ cuộc sớm.
- **Thực thi mẫu (trên Client/Server):**

  ```python
  import torchaudio
  # Load Silero VAD (chạy siêu nhanh trên CPU)
  vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
  (get_speech_timestamps, _, _, _, _) = utils
  
  speech_timestamps = get_speech_timestamps(wav, vad_model, sampling_rate=16000)
  # Tiến hành gửi/decode từng timestamp độc lập
  ```

#### 🟡 Phương án 2B: Giải quyết Vòng Lặp Bằng Chunking Độc lập

Khi xử lý file dài, việc ghép transcript hoặc truyền context lộn xộn có thể khiến đoạn hội thoại tiếp theo cố "kết dính" ngữ nghĩa với câu kính ngữ bị lỗi trước đó $\rightarrow$ mô hình bế tắc và ngắt lời. Vì `Voxtral-Mini-4B` không có tham số `condition_on_previous_text=False` như Whisper, ta cần:

- **Thực thi:**
  1. Xử lý mỗi đoạn audio chunk (được cắt bởi VAD) một cách hoàn toàn độc lập, không append text của chunk trước vào `processor(text=..., audio=...)`.
  2. Bắt buộc kết hợp với Prefix Prompting (như Phương án 1A) ở mỗi chunk độc lập để giữ mạch ngôn ngữ.

- **Trade-off:** Đảm bảo các đoạn nhỏ xử lý độc lập với nhau. Nếu 1 cửa sổ chết, cửa sổ n+1 vẫn sống lại bình thường.

#### 🟢 Phương án 2C: Điều chỉnh Tham số Fallback & Sampling

Kiến trúc `Voxtral-Mini-4B` dựa trên `transformers.generate`, vì vậy ta có thể ghi đè một số tham số fallback để tránh token EOF `<|endoftext|>` sớm:

- **Thực thi:**
  1. Hủy bỏ do_sample cho inference mặc định (`temperature=0.0`) để có độ tin cậy cao nhất.
  2. Bật tham số Fallback vòng lặp ở client: Nếu chuỗi output quá ngắn hoặc bị lặp, tự động gửi request lại với `temperature=0.2`.
  3. *(Tùy chọn)* Dùng `length_penalty` âm/dương trong `generate()` nếu tài liệu model support để điều hướng độ dài chuỗi dự đoán. Cần kiểm chứng cẩn thận vì tham số này có thể làm nhiễu xác suất output.

---

## 3. Tổng kết Kế hoạch Đề xuất

Để tối ưu nhanh nhất thời gian và nhân lực cho Voxtral, lộ trình sau được khuyến nghị:

| Thứ tự | Mục tiêu | Lựa chọn tốt nhất (Từ danh sách trên) | Thời gian triển khai |
| :--- | :--- | :--- | :--- |
| **Bước 1** | **Khắc phục ngay CER 100% do sai ngôn ngữ** | **Phương án 1A:** Truyền Prefix Prompt (`text="[Tiếng Nhật]"`) vào processor trong `voxtral_server_transformers.py`. | ~1 giờ (Chỉnh sửa inference script) |
| **Bước 2** | **Loại bỏ Early Truncation & Hallucinations do Chunk Nhiễu** | **Phương án 2A:** Tích hợp `Silero VAD` làm tiền xử lý trước ASR để cắt Chunk sạch. | ~1-2 ngày (Cần refactor pipeline phía Client/Server) |
| **Bước 3** | **Chống vòng lặp (Looping) & Cải thiện độ ổn định** | **Phương án 2B & 2C:** Đảm bảo mỗi chunk xử lý độc lập hoàn toàn, thêm Fallback Temperature=0.2 khi gặp output bất thường. | ~1 ngày |
