# Tổng hợp Phân tích Vấn đề Hiệu suất ASR (Voxtral)

Tài liệu này tổng hợp các vấn đề chính ảnh hưởng đến hiệu suất nhận dạng giọng nói, nguyên nhân gốc rễ, và lộ trình giải pháp đề xuất theo thứ tự ưu tiên.

## 1. Các Vấn đề Chính (Problems)

- **Tỷ lệ lỗi cao (CER > 80%):** Nhiều tập tin có kết quả nhận dạng sai lệch hoàn toàn so với thực tế. Voxtral đạt CER trung bình 45.0%, Javis đạt 34.7%.
- **Các loại Ảo giác (Hallucination Types):**
  - **Insertion (Chèn từ):** Đây là lỗi phổ biến nhất ở cả hai hệ thống — Voxtral 54.54%, Javis 79.09%. AI tự chèn thêm các cụm từ không có trong audio để lấp đầy khoảng trống.
  - **Looping (Lặp vòng):** Đặc biệt ở Javis, xuất hiện các chuỗi lặp vô tận của một cụm từ (ví dụ: "Cảm ơn, vâng, tôi biết rồi..."). CER có thể dao động 28%–95% trên cùng một file giữa các lần chạy.
  - **Content Replacement (Thay thế nội dung):** Voxtral có tỷ lệ cao hơn 3.5 lần so với Javis (6.36% vs 1.81%), thường thay thế hoàn toàn nội dung gốc bằng cụm từ lịch sự kiểu Nhật (Keigo).
- **Nhận diện sai ngôn ngữ (Language Collapse):** Khi chất lượng âm thanh kém, Voxtral rơi vào "vùng an toàn" và xuất ra ngôn ngữ khác hoàn toàn (ví dụ: file tiếng Nhật `media_148414` xuất ra "Hi, Joseph. I'm sorry." → CER cố định 100% qua mọi lần chạy).
- **Ngắt lời sớm (Early Truncation):** AI dừng nhận dạng trước khi hội thoại kết thúc. Ví dụ: `media_149291` dài 156.7 giây thoại nhưng Voxtral chỉ xuất vài từ → CER 97.8%.

## 2. Nguyên nhân Gốc rễ (Root Causes)

### 2.1. Băng thông hẹp (Narrowband) & Naive Upsampling

Âm thanh từ hệ thống điện thoại bị cắt ở dải tần số **1.9 kHz – 2.4 kHz** (rolloff), khiến các phụ âm cao tần (fricatives) như "s", "x", "th", "f" bị mất hoàn toàn. Code hiện tại (`librosa.load(..., sr=16000)`) chỉ là phép nội suy tuyến tính — giống phóng to ảnh mờ: kích thước tăng nhưng không sinh thêm chi tiết. Mô hình ASR phải đoán mò phụ âm, dẫn đến CER cao.

> **Bằng chứng:** Tất cả file poor ASR cases đều có rolloff 1891–2554 Hz. Không có bước Bandwidth Expansion trong code hiện tại.

### 2.2. Thiếu Language Hint — Language Collapse

Voxtral tự động nhận diện ngôn ngữ (auto-detect), trong khi Javis được **chỉ định cứng** `language: "ja"` trong [run_asr_javis.py](file:///d:/VJ/Voxtral/run_asr_javis.py). Khi âm thanh quá nhiễu, Voxtral mất phương hướng và rơi vào ngôn ngữ quen thuộc nhất (thường là tiếng Anh), gây **CER 100%** và lỗi mang tính hệ thống (lặp lại qua mọi lần chạy).

> **Bằng chứng:** `media_148414` — Voxtral luôn xuất tiếng Anh, CER cố định 100%, transcript hash bất biến qua 15 runs. Javis trên cùng file chỉ CER ~40% nhờ Language Hint.

### 2.3. Thiếu Voice Activity Detection (VAD)

Ảo giác Insertion cực kỳ phổ biến khi mô hình cố gắng "giải mã" tiếng ồn nền (quạt, gõ phím) hoặc các khoảng lặng dài thành lời nói. Hiện **không có bước lọc bỏ silence/noise** trước khi gửi vào ASR.

> **Bằng chứng:** Insertion là lỗi phổ biến nhất — Voxtral 54.54%, Javis 79.09%. Các đoạn noise trong file bị cường ép giải mã thành text.

### 2.4. Vòng lặp phản hồi — Condition on Previous Text

Hiện tượng Looping xảy ra khi mô hình lấy output của đoạn trước làm context cho đoạn sau. Nếu đoạn trước bị nhận diện sai, mô hình bị "kẹt" trong vòng lặp xác suất và lặp lại vô tận khi gặp âm thanh nhiễu.

> **Bằng chứng:** `media_148439` Javis — lặp tiếng Hàn dài hàng trăm ký tự. Std CER 23.9% cho thấy lỗi mang tính xác suất, không tất định.

### 2.5. Cơ chế Giải mã & Early Truncation

Khi confidence score giảm đột ngột dưới ngưỡng `no_speech_threshold` (do gặp nhiễu hoặc khoảng lặng dài), Voxtral quyết định đó là kết thúc hội thoại và dừng giải mã sớm — đặc biệt nghiêm trọng trên file dài.

> **Bằng chứng:** `media_149291` — 156.7s thoại nhưng Voxtral chỉ xuất hypothesis cực ngắn, CER 97.8%, hallucination rate 0% (không sai — chỉ thiếu).

### 2.6. Chiến lược Giải mã Khác biệt (Voxtral vs Javis)

Đây là nguyên nhân giải thích **Nghịch lý CER vs Hallucination**: Javis có CER tốt hơn (34.7%) nhưng hallucination cao hơn (90.0%), trong khi Voxtral có hallucination thấp hơn (71.5%) nhưng CER cao hơn (45.0%).

- **Voxtral** ưu tiên "sạch sẽ" — khi không tự tin thì bỏ cuộc (truncation) hoặc sập ngôn ngữ → nhiều bản dịch OK nhưng số ít sai thì CER cực cao.
- **Javis** ưu tiên "giữ cấu trúc" — cố gắng tạo output có vẻ hợp lý kể cả khi không nghe rõ → CER thấp hơn tổng thể nhưng đa số bản dịch đều có insertion.

## 3. Giải pháp Đề xuất (Solutions) — Theo thứ tự Ưu tiên

### 🔴 Ưu tiên 1: Tích hợp Silero VAD (Chống Insertion & Giảm tải)

**Nguyên nhân giải quyết:** §2.3 (Thiếu VAD) + hỗ trợ §2.5 (Early Truncation)

```
Pipeline mới: Audio → Silero VAD → Chỉ gửi speech chunks → ASR
```

- **Silero VAD** (~2MB) chạy trên CPU, latency <50ms
- Cấu hình khuyến nghị: `threshold=0.5`, `min_speech_duration_ms=250`, `min_silence_duration_ms=100`
- **Tác động dự kiến:** Giảm 55–80% insertion rate (hiện 54.54% Voxtral), triệt tiêu hoàn toàn ảo giác trên silence/noise segments
- **Độ phức tạp:** Thấp — thêm một node trước pipeline hiện tại

### 🔴 Ưu tiên 2: Language Hint / LID Độc lập (Chống Language Collapse)

**Nguyên nhân giải quyết:** §2.2 (Thiếu Language Hint)

- **Phương án A (Nhanh, cho domain cố định):** Chỉ định cứng `language="ja"` trong config — tương tự cách Javis đã triển khai thành công
- **Phương án B (Linh hoạt, đa ngôn ngữ):** Chạy Whisper-tiny ở LID-only mode (~39MB) → xác định ngôn ngữ → truyền vào Voxtral
- **Tác động dự kiến:** Loại bỏ hoàn toàn Language Collapse. File `media_148414` dự kiến giảm từ CER 100% xuống ~35–40%
- **Độ phức tạp:** Rất thấp (A) / Thấp (B)

### 🟡 Ưu tiên 3: Quản lý Context & Prompt Biasing (Sửa lỗi Phụ thuộc Context)

**Nguyên nhân giải quyết:** §2.4 (Looping) và một phần Language Collapse

Do kiến trúc `Voxtral-Mini-4B` không hỗ trợ tham số `condition_on_previous_text` như Whisper, việc phá vòng lặp hội thoại hoặc ép ngôn ngữ cần thực hiện qua **Text Prompting** ở lớp Processor:

```python
# Chèn prefix text trước khi đưa vào mô hình để dẫn dắt ngôn ngữ và ngữ cảnh
inputs = processor(text="[Tiếng Nhật] ", audio=audio_obj.audio_array, return_tensors="pt")
```

- **Tác động dự kiến:** Khởi tạo context sạch cho mỗi chunk, dẫn dắt mô hình dịch sang ngôn ngữ đích (Tiếng Nhật) ngay từ đầu, phá vỡ ảnh hưởng của các câu rác tạo ra vòng lặp.
- **Độ phức tạp:** Thấp — sửa tham số `text` trong `processor()`.

### 🟡 Ưu tiên 4: Chiến lược Chunking (Overlapping)

**Nguyên nhân giải quyết:** §2.5 (Early Truncation ở file dài)

- Sử dụng **VAD boundaries** (từ giải pháp #1) làm điểm cắt tự nhiên thay vì cắt cứng theo thời gian
- **Overlap** ~1–2 giây giữa các chunk liền kề
- Hợp nhất bằng timestamp alignment, loại bỏ duplicate text
- **Tác động dự kiến:** Giải quyết `media_149291` (CER 97.8% do truncation trên file 156s)
- **Độ phức tạp:** Trung bình — cần logic merge transcript

### 🟢 Ưu tiên 5: Tối ưu Fallback Sampling (Thay thế no_speech_threshold)

**Nguyên nhân giải quyết:** Hạn chế ảo giác khi gặp nhiễu bằng cách thêm cơ chế fallback.

Kiến trúc Voxtral hiện tại không có `no_speech_threshold` nội tại. Do đó, cần thiết lập Fallback Temperature ở client/server:

- Nếu bản dịch xuất ra rỗng chứa toàn ký tự lặp hoặc quá ngắn, tiến hành gửi lại request với `temperature=0.2` (hoặc cao hơn) để cung cấp tính đa dạng giải mã.
- Kết hợp với VAD (Giải pháp 1) để đảm bảo mô hình không bao giờ phải xử lý "rác âm thanh".

- **Độ phức tạp:** Thấp - Trung bình.

### 🟢 Ưu tiên 6: Luồng Tiền xử lý âm thanh nâng cao (Advanced Audio Preprocessing Pipeline)

**Nguyên nhân giải quyết:** §2.1 (Narrowband), §2.3 (Noise/Insertion), §2.5 (Early Truncation) và làm rõ cấu trúc âm học.

Tuy có độ phức tạp cộng dồn cao và có thể làm giảm tốc độ (tăng RTF), đây là danh sách đầy đủ các kỹ thuật có thể áp dụng để xử lý triệt để chất lượng đầu vào. Trong quá trình triển khai và kiểm thử, nhóm phát triển có thể chọn lọc bật/tắt từng module để tìm điểm cân bằng tối ưu giữa cấu hình hardware, tốc độ và độ chính xác:

1. **Bandpass Filtering (Lọc băng thông):**
   - Áp dụng High-pass và Low-pass filter cắt bỏ các dải tần số "rác" (như tiếng ầm máy móc < 50Hz ngoài giọng nói con người), làm sạch nền đầu vào trước khi qua các hệ thống nâng cao khác (đặc biệt hữu ích khi kết hợp với Super Resolution).
2. **Loudness Normalization / Volume Normalization (Chuẩn hóa âm lượng):**
   - Cân bằng tín hiệu thoại để duy trì ở một mức (dB) chuẩn không đổi. Giúp giải quyết hiện tượng âm lượng thu nhỏ đột ngột khiến confidence của mô hình bị rớt, từ đó ngăn chặn chủ động lỗi **Early Truncation** (bỏ ngắt sớm).
3. **Dereverberation (Khử tiếng vang/vọng):**
   - Loại bỏ tiếng vọng không gian (room acoustics) hoặc tiếng vang dội từ đường truyền điện thoại. Điều này giúp các âm tiết trở nên sắc nét hơn, hạn chế tình trạng chồng lấp (smearing) âm, hỗ trợ mô hình nhận cắt độ dài của từ chính xác hơn.
4. **Noise Reduction / Denoising (Giảm nhiễu nền):**
   - Sử dụng các giải pháp deep learning nhẹ như **DeepFilterNet** (tối ưu hơn Demucs trên CPU). Giúp cô lập giọng nói và triệt tiêu tiếng ồn môi trường, giải quyết tận gốc lượng khổng lồ ảo giác **Insertion** (do mô hình cố gắng dịch nhiễu thành text).
5. **AI Restoration — Bandwidth Extension / Super Resolution (Dài hạn & Nặng):**
   - Sử dụng các mô hình phục hồi âm thanh như **AudioSR** để tạo nội suy, bù đắp các dải tần số cao bị tổng đài cắt mất phần cứng (rolloff 1.9k - 2.4kHz). Việc khôi phục các phụ âm biên độ cao như "s", "x", "th" sẽ là phương án khắc phục dứt điểm nguyên nhân **Root Cause 2.1**. Đòi hỏi lượng RAM và GPU rất lớn.

- **Thứ tự áp dụng Pipeline khuyến nghị:** `Bandpass → Normalization → (VAD: Ưu tiên 1) → Denoising + Dereverberation → Extension/Super Resolution → Voxtral ASR`.
- **Tác động dự kiến:** Khắc phục gần như mọi nhược điểm do đầu vào kém, CER có thể giảm cực sâu.
- **Độ phức tạp:** Rộng (trải từ Thấp đến Rất cao tuỳ vào số module bật). Khuyến nghị triển khai dạng plug-and-play để dễ đánh giá.

## 4. Kết luận & So sánh Tổng quan (Conclusion)

Dựa trên dữ liệu thực nghiệm từ [hallucination_analysis.md](file:///d:/VJ/Voxtral/reports/hallucination_analysis.md), [comparison.md](file:///d:/VJ/Voxtral/reports/comparison.md), và [voxtral_vs_javis_detailed_per_file.md](file:///d:/VJ/Voxtral/reports/voxtral_vs_javis_detailed_per_file.md):

| Chỉ số (Metrics) | Voxtral | Javis | Nhận xét |
| --- | ---: | ---: | --- |
| **CER trung bình (11 file)** | 45.0% | **34.7%** | Javis chính xác hơn ~10%. |
| **CER trung bình (9 GT file)** | 55.0% | **42.4%** | Bỏ 2 file silence/noise, chênh lệch rõ hơn. |
| **Tỷ lệ ảo giác** | **71.5%** | 90.0% | Voxtral "sạch sẽ" hơn. CI: 64.2%–77.9% vs 83.0%–94.3%. |
| **Tỷ lệ nghiêm trọng cao** | **30.9%** | 36.4% | Voxtral rủi ro sai lệch nghiêm trọng thấp hơn nhẹ. |
| **Tốc độ (RTF)** | 1.677 | **0.006** | Javis nhanh hơn ~280 lần (inference on-premise vs API T4). |
| **Độ ổn định CER** | **Bất biến** | Dao động | Std CER Voxtral = 0%, Javis lên đến 72.4% (`media_149291`). |

> **Lưu ý phạm vi dữ liệu:** Tỷ lệ ảo giác 71.5%/90.0% tính trên toàn bộ inference records (15 runs Voxtral, 10 runs Javis, 275 records). Báo cáo `voxtral_vs_javis_detailed_per_file.md` lọc riêng 10 runs (v1-v10) và loại silence/noise files, cho ra 60.91%/80.91%.

**Đánh giá tổng hợp:**

- **Voxtral:** Có xu hướng "trung thực" hơn (tỷ lệ ảo giác thấp hơn, output ổn định giữa các runs), nhưng dễ bị **Language Collapse** khi gặp âm thanh chất lượng kém, dẫn đến CER cố định 100% ở một số file. Khi sai, sai mang tính hệ thống và không phục hồi.
- **Javis:** Dù có tỷ lệ ảo giác cao hơn, nhưng nhờ **Language Hint** (`language: "ja"`), Javis duy trì được cấu trúc hội thoại và tránh được Language Collapse. Tuy nhiên, Javis bất ổn định giữa các runs (10 transcript hash khác nhau cho cùng 1 file) và dễ rơi vào looping.

**Kết luận cuối cùng:** Hiệu suất Voxtral hiện bị giới hạn bởi **3 yếu tố có thể khắc phục ngay**: (1) thiếu VAD filter, (2) thiếu Language Hint/Prompt via text, và (3) sự thiếu linh hoạt trong xử lý Chunking. Đặc biệt, vì `Voxtral-Mini-4B` không có các tham số cắt cứng nhiễu (như Whisper), Giải pháp tích hợp **Silero VAD (Ưu tiên 1)** là **bắt buộc** để xóa bỏ hiện tượng Looping và Early Truncation một cách triệt để nhất. Các giải pháp bổ trợ (Prompting) sẽ thu hẹp đáng kể khoảng cách CER với Javis.

## 5. Lưu ý về Đánh giá (Evaluation Artifacts)

Cần phân biệt giữa lỗi của engine ASR và nhiễu từ tầng đánh giá:

- **Lỗi Silence_text:** Một số trường hợp "ảo giác" trên các đoạn im lặng (silence) thực chất là "artifact" của lớp LLM-evaluator khi cố gắng gán nghĩa cho các đoạn không có thoại. Điều này không phản ánh hoàn toàn năng lực của model ASR.
- **Dao động nhãn LLM-eval:** Với Voxtral, transcript hash bất biến giữa các runs nhưng nhãn severity từ LLM-eval vẫn dao động ở một số file — cho thấy tầng đánh giá có **độ nhiễu riêng** cần cân nhắc khi diễn giải kết quả.
- **CER trên silence/noise files:** Cả hai engine đều đạt CER 0% trên `silence_60s.wav` và `stochastic_noise_60s.wav`, do đó các file này không được đưa vào bảng high-severity chính.
