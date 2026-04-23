# Báo cáo Phân tích Chi tiết: Tại sao CER > 80%?

Khi chỉ số **CER (Character Error Rate)** vượt quá 80%, điều đó có nghĩa là kết quả nhận dạng gần như sai hoàn toàn so với thực tế. Dựa trên dữ liệu truy vết, có 3 nhóm nguyên nhân chính "hủy diệt" độ chính xác của hệ thống:

## 1. Chất lượng âm thanh "Băng thông hẹp" (Narrowband)

Đây là "kẻ thù" lớn nhất của AI. Hầu hết các file bị lỗi nặng đều có chỉ số **Rolloff** thấp (dưới 2.4 kHz).

### Băng thông (Bandwidth) là gì?

Hãy tưởng tượng âm thanh như các dòng nước chảy qua một **đường ống**:

- **Băng thông rộng (Broadband/HD Audio):** Giống như một cái ống lớn. Nó dẫn được cả "phần thân" tiếng nói (âm trầm, âm chính) và "phần ngọn" (các âm gió sắc nét như s, x, ch, t).
- **Băng thông hẹp (Narrowband/Telephony):** Giống như một ống hút nhỏ. Nó chỉ dẫn được phần "thân" lùng bùng, còn phần "ngọn" sắc sảo bị chặn lại hoàn toàn.

### Tại sao nó lại là "kẻ thù" của AI?

Tiếng nói con người có hai thành phần chính:

1. **Nguyên âm (A, E, O...):** Tần số thấp (trầm), dễ truyền đi.
2. **Phụ âm (S, T, PH, TR...):** Tần số rất cao (thanh). Đây là những âm giúp ta **phân biệt** các từ (ví dụ: "xa" khác "sa" nhờ âm gió).

Khi băng thông hẹp (giống như các cuộc gọi điện thoại cũ), toàn bộ các phụ âm cao này bị "gọt" sạch.

- **Dễ hiểu là:** Giống như bạn xem một bức ảnh bị mờ hết các đường nét sắc sảo, chỉ còn lại những mảng màu lem nhem.
- **Hệ quả đối với AI:** AI nghe thấy một chuỗi âm thanh lùng bùng ("a... e... o..."). Vì không phân biệt được từ, nó buộc phải **tự điền vào chỗ trống** dựa trên xác suất, dẫn đến hiện tượng ảo giác (Hallucination).

### Các yếu tố ảnh hưởng đến Băng thông

1. **Thiết bị ghi âm (Hardware):** Mic cũ hoặc rẻ tiền không có khả năng thu được âm thanh ở tần số cao.
2. **Tần số lấy mẫu (Sampling Rate):** Đây là thông số kỹ thuật (ví dụ 8kHz, 16kHz). Nếu file ghi ở 8kHz, băng thông tối đa chỉ đạt được 4kHz (Narrowband).
3. **Giao thức truyền tải (Codec):** Các cuộc gọi điện thoại truyền thống (sim điện thoại) thường nén âm thanh rất nặng để tiết kiệm dung lượng, làm "gọt" sạch băng thông. Các ứng dụng như Zalo, Telegram dùng công nghệ mới hơn nên có băng thông rộng hơn.

### Có thể thiết lập băng thông cao hơn không?

- **Với file đã ghi âm (Narrowband):** Rất khó. Bạn không thể "phục hồi" dữ liệu đã mất một cách hoàn hảo. AI có thể dùng công nghệ "Audio Super-Resolution" để bù đắp, nhưng đó vẫn chỉ là phỏng đoán, không phải dữ liệu thật.
- **Giải pháp triệt để:** Cần thay đổi ở bước **Đầu vào**. Cấu hình thiết bị ghi âm hoặc hệ thống tổng đài thu âm ở tần số lấy mẫu ít nhất là 16kHz (Wideband) để AI có đủ "nguyên liệu" làm việc.

## 2. Các kịch bản thất bại cụ thể (Failure Modes)

### A. "Sập" ngôn ngữ (Language Collapse)

- **File điển hình:** `media_148414... (Voxtral)`
- **Hiện tượng:** Âm thanh là tiếng Nhật, nhưng AI lại xuất ra tiếng Anh (ví dụ: "Hi, Joseph. I'm sorry").
- **Lý do:** Khi âm thanh quá nhiễu hoặc mờ, AI bị mất phương hướng và rơi vào "vùng an toàn" là các câu tiếng Anh phổ biến mà nó đã học, thay vì cố gắng nhận diện tiếng Nhật.

### B. Vòng lặp ảo giác (Looping Hallucination)

- **File điển hình:** `media_148439... (Javis)`
- **Hiện tượng:** AI lặp đi lặp lại một cụm từ tiếng Hàn (ví dụ: "Cảm ơn, vâng, tôi biết rồi, cảm ơn...") trong khi thực tế là tiếng Nhật.
- **Lý do:** Bộ giải mã bị kẹt trong một vòng lặp xác suất. Nó nghĩ rằng cụm từ đó có khả năng đúng cao nhất và cứ thế lặp lại vô tận để "lấp đầy" đoạn âm thanh mà nó không hiểu.

### C. Ngắt lời sớm (Early Truncation)

- **File điển hình:** `media_149291... (Voxtral)`
- **Hiện tượng:** File dài hơn 2 phút nhưng AI chỉ dịch được vài từ rồi dừng lại.
- **Lý do:** AI hiểu lầm các đoạn âm thanh mờ hoặc im lặng là "kết thúc câu" (End of Sentence) và tự động đóng kết nối sớm, bỏ qua toàn bộ phần sau của hội thoại.

## 3. Sự khác biệt giữa hai hệ thống

- **Voxtral (Ổn định nhưng sai hệ thống):** Nếu Voxtral sai ở một file, nó sẽ luôn sai ở file đó qua mọi lần chạy. Điều này cho thấy lỗi nằm ở "kiến thức" của mô hình đối với loại âm thanh đó.
- **Javis (Bất ổn định):** Cùng một file, lần chạy này có thể đúng một chút, lần sau lại sai be bét (lopping). Điều này cho thấy thuật toán tìm kiếm từ của Javis dễ bị phân tâm bởi nhiễu.

## 4. Phân tích mã nguồn xử lý (Code Review)

Tôi đã kiểm tra kỹ file [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py) và [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py). Hiện tại, quy trình xử lý âm thanh như sau:

1. **Upsampling (Tăng tần số lấy mẫu):** Cả client và server đều sử dụng lệnh `librosa.load(..., sr=16000)`.
   - **Tác dụng:** Chuyển đổi mọi file (kể cả 8kHz) về chuẩn 16kHz để khớp với yêu cầu của mô hình Voxtral.
   - **Hạn chế:** Đây chỉ là phép **nội suy tuyến tính** (linear interpolation). Nó giống như việc bạn phóng to một bức ảnh pixel thấp; kích thước ảnh to hơn nhưng nội dung vẫn bị mờ, không hề sinh thêm "độ nét" thật sự.

2. **Thiếu Bandwidth Expansion (BWE):** Trong code hiện tại **không có** bước xử lý AI để phục hồi các tần số bị mất. AI nhận được một file 16kHz nhưng thực chất chỉ có 4kHz dữ liệu thật.

### Có cách nào làm băng thông rộng hơn trong code không?

Có thể, nhưng cần bổ sung thêm thư viện và mô hình bổ trợ:

- **Audio Super-Resolution:** Thêm các mô hình như `VoiceFixer` hoặc `NuWave` vào trước bước `model.generate`. Các mô hình này sẽ "vẽ thêm" các tần số cao dựa trên đặc trưng giọng nói hiện có.
- **Spectral Normalization:** Cân bằng lại phổ âm thanh để làm nổi bật các tín hiệu yếu ở dải cao.

## 5. So sánh Javis vs Voxtral: Tại sao Javis lại tốt hơn?

Mặc dù cả hai đều dùng chung mức băng thông (đều upsample lên 16kHz), Javis thường cho kết quả tốt hơn ở các file narrowband nhờ 3 lý do kỹ thuật sau:

### 1. Chỉ định ngôn ngữ (Language Hint)

- **Voxtral:** Tự động nhận diện ngôn ngữ. Khi âm thanh quá tệ (narrowband), Voxtral dễ đoán sai ngôn ngữ (ví dụ nhầm tiếng Nhật thành tiếng Anh).
- **Javis:** Trong code ([run_asr_javis.py](file:///d:/VJ/Voxtral/run_asr_javis.py)), Javis được chỉ định sẵn `"language": "ja"`. Điều này giúp AI không bị lạc hướng và tập trung vào việc tìm các từ tiếng Nhật phù hợp nhất thay vì đoán mò sang ngôn ngữ khác.

### 2. Công nghệ giảm nhiễu nâng cao (Advanced Denoising)

- Javis tích hợp sẵn các bộ khử nhiễu mạnh như **Demucs** (một mô hình deep learning chuyên nghiệp để tách âm thanh).
- Khi đối mặt với file điện thoại cũ, Javis có thể "gạt" nhiễu tốt hơn để lộ ra các đặc trưng giọng nói còn sót lại, trong khi Voxtral xử lý trực tiếp trên file gốc hoặc các bộ lọc cơ bản.

### 3. Chiến lược giải mã (Decoding Strategy)

- Khi độ tự tin thấp, Voxtral có xu hướng **"bỏ cuộc"** (ngắt sớm - Truncation) hoặc **"sập"** hoàn toàn.
- Javis có xu hướng **"nỗ lực giữ cấu trúc"**. Kể cả khi không nghe rõ, Javis vẫn cố gắng tạo ra một chuỗi hội thoại có cấu trúc gần giống thực tế hơn, giúp giảm CER so với việc bỏ sót hoàn toàn nội dung.

## 6. Cơ chế khử nhiễu: Trong Model hay trong Code?

Đây là một câu hỏi rất hay về kiến trúc hệ thống. Câu trả lời là: **Nó nằm ở lớp Code (Pre-processing), không nằm trong "não" (weights) của model ASR.**

### Javis làm như thế nào?

- Khi bạn gửi âm thanh đến Javis, hệ thống không đưa thẳng vào model ASR ngay.
- Nó đi qua một "phòng lọc" (Preprocessing Layer) nằm trong code server. Tại đây, Javis có khả năng chạy một model khác chuyên biệt cho việc khử nhiễu (như **Demucs**).
  - **Đính chính về thực tế chạy:** Mặc dù code Javis có hỗ trợ Demucs, nhưng trong các lần chạy benchmark vừa qua (theo cấu hình mặc định), tính năng này **chưa được bật**. Điều này có nghĩa là kết quả tốt của Javis hiện tại đến từ các yếu tố khác (như ngôn ngữ) chứ không phải do bộ lọc này.
- Sau khi âm thanh đã "sạch" (hoặc xử lý trực tiếp), nó mới được đưa vào model ASR để dịch thành văn bản.

---

---
> [!IMPORTANT]
> **Kết luận:** Javis thắng thế chủ yếu nhờ có **gợi ý ngôn ngữ (Language Hint)** giúp định hướng tốt trong môi trường nhiễu. Tuy nhiên, Javis còn một "vũ khí bí mật" là bộ khử nhiễu AI (Demucs) chưa được sử dụng; nếu bật tính năng này lên, khoảng cách giữa Javis và Voxtral có thể còn xa hơn nữa.
