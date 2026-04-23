# Tổng hợp Phân tích Vấn đề Hiệu suất ASR (Voxtral)

Tài liệu này tổng hợp các vấn đề chính ảnh hưởng đến hiệu suất nhận dạng giọng nói, nguyên nhân và các hướng giải pháp đề xuất.

## 1. Các Vấn đề Chính (Problems)

- **Tỷ lệ lỗi cao (CER > 80%):** Nhiều tập tin có kết quả nhận dạng sai lệch hoàn toàn so với thực tế.
- **Các loại Ảo giác (Hallucination Types):**
  - **Insertion (Chèn từ):** Đây là lỗi phổ biến nhất, AI tự chèn thêm các cụm từ không có trong audio để lấp đầy khoảng trống.
  - **Looping (Lặp vòng):** Đặc biệt ở Javis, xuất hiện các chuỗi lặp vô tận của một cụm từ (ví dụ: "Cảm ơn, vâng, tôi biết rồi...").
- **Nhận diện sai ngôn ngữ:** Hệ thống tự động nhận diện nhầm ngôn ngữ khi chất lượng âm thanh kém (ví dụ: tiếng Nhật bị nhận diện thành tiếng Anh).
- **Ngắt lời sớm (Early Truncation):** AI dừng nhận dạng trước khi hội thoại kết thúc, khiến kết quả bị thiếu hụt nghiêm trọng.

## 2. Nguyên nhân Gốc rễ (Causes)

- **Băng thông hẹp (Narrowband) & Naive Upsampling:** Âm thanh bị cắt ở dải tần số **1.9 kHz - 2.4 kHz** khiến các âm xát (fricatives) như "s", "x", "th", "f" biến mất hoặc bị biến dạng. Việc nội suy tuyến tính (upsampling) thông thường chỉ là "phóng to một bức ảnh mờ", mô hình phải đoán mò phụ âm, dẫn đến CER cao.
- **Cơ chế Giải mã & Sập hệ thống (Early Truncation):** Việc AI "bỏ cuộc" thường do confidence score giảm đột ngột dưới ngưỡng `no_speech_threshold` khi gặp nhiễu hoặc khoảng lặng dài. AI quyết định đó là kết thúc hội thoại và dừng giải mã sớm.
- **Vòng lặp phản hồi (Condition on Previous Text):** Hiện tượng Looping (ảo giác lặp từ) xảy ra khi mô hình lấy output của đoạn trước làm context cho đoạn sau. Nếu đoạn trước bị nhận diện sai thành một cụm từ vô nghĩa, mô hình sẽ bị "kẹt" và lặp lại liên tục khi gặp âm thanh nhiễu.
- **Thiếu Voice Activity Detection (VAD) chuẩn xác:** Ảo giác Insertion (chèn từ) cực kỳ phổ biến khi mô hình cố gắng "giải mã" tiếng ồn nền (quạt, gõ phím) hoặc các khoảng lặng dài thành lời nói mà không có bước lọc bỏ silence/noise trước.

## 3. Giải pháp Đề xuất (Solutions)

- **Tích hợp Silero VAD (Chống Hallucination):** Đặt một node VAD cực nhẹ và chính xác ngay đầu pipeline để chỉ gửi những chunk âm thanh thực sự có tiếng người vào ASR. Điều này triệt tiêu gần như 100% ảo giác chèn từ (Insertion).
- **Chiến lược Chunking (Overlapping):** Sử dụng VAD để cắt ở những chỗ im lặng, hoặc sử dụng Overlapping chunks (đoạn sau gối lên đoạn trước ~1-2 giây) rồi hợp nhất văn bản để khắc phục lỗi Early Truncation ở cuối file.
- **Tối ưu Denoising (DeepFilterNet):** Sử dụng DeepFilterNet thay vì Demucs cho mục tiêu ASR thuần túy vì tốc độ suy luận nhanh hơn và bảo toàn dải âm giọng nói tốt hơn trên các thiết bị không có GPU.
- **Quản lý Context (Tắt Condition on Previous Text):** Nếu AI thường xuyên bị lặp từ (Looping), việc tắt `condition_on_previous_text` sẽ hy sinh một chút sự trôi chảy nhưng loại bỏ hoàn toàn hiện tượng lặp lại vô tận.
- **Tối ưu Prompting / Context Biasing:** Sử dụng tham số `initial_prompt` hoặc danh sách từ vựng domain để định hướng vocabulary cho mô hình từ giây đầu tiên thay vì dùng "Dummy Audio".
- **AI Restoration (Bandwidth Expansion):** Sử dụng các mô hình như AudioSR để tái tạo các tần số bị mất (phức tạp và tốn tài nguyên hơn nhưng hiệu quả cao).
- **Tầng nhận diện ngôn ngữ (LID) độc lập:** Chạy một model LID siêu nhẹ (như Whisper-tiny LID mode) trước để cứu luồng ASR khỏi việc dịch sai ngôn ngữ khi gặp nhiễu.

## 4. Kết luận & So sánh Tổng quan (Conclusion)

Dựa trên dữ liệu thực nghiệm từ [comparison.md](file:///d:/VJ/Voxtral/reports/comparison.md) và [hallucination_analysis.md](file:///d:/VJ/Voxtral/reports/hallucination_analysis.md), ta có cái nhìn tổng quan về hiệu suất của hai hệ thống:

| Chỉ số (Metrics) | Voxtral | Javis | Nhận xét |
| --- | ---: | ---: | --- |
| **CER trung bình** | 45.0% | **34.7%** | Javis chính xác hơn về mặt ký tự (~10%). |
| **Tỷ lệ ảo giác** | **71.5%** | 90.0% | Javis thường xuyên sinh ra nội dung thừa hơn. |
| **Tỷ lệ nghiêm trọng cao** | **30.9%** | 36.4% | Javis có rủi ro sai lệch nghiêm trọng cao hơn nhẹ. |
| **Tốc độ (RTF)** | 1.677 | **0.006** | Javis nhanh hơn vượt trội. |

**Đánh giá tổng hợp:**

- **Voxtral:** Có xu hướng "trung thực" với dữ liệu hơn (tỷ lệ ảo giác thấp hơn), nhưng lại dễ bị **"sập" hệ thống (Language Collapse)** khi gặp âm thanh chất lượng kém, dẫn đến CER tăng vọt lên 100% ở một số file cụ thể.
- **Javis:** Dù có tỷ lệ ảo giác cao hơn, nhưng nhờ được **chỉ định ngôn ngữ (Language Hint)**, Javis duy trì được cấu trúc hội thoại và tránh được lỗi sai ngôn ngữ, giúp đạt CER thấp hơn Voxtral trên hầu hết các file kiểm thử.

**Kết luận cuối cùng:** Hiệu suất của Voxtral hiện bị giới hạn chủ yếu bởi chất lượng âm thanh đầu vào và việc thiếu định hướng ngôn ngữ. Trong khi đó, Javis đạt kết quả khả quan hơn một phần nhờ lợi thế được **chỉ định cứng ngôn ngữ (Language Hint: "ja")** trong mã nguồn test, giúp giảm thiểu rủi ro "sập" ngôn ngữ khi gặp nhiễu.

## 5. Lưu ý về Đánh giá (Evaluation Artifacts)

Cần phân biệt giữa lỗi của engine ASR và nhiễu từ tầng đánh giá:

- **Lỗi Silence_text:** Một số trường hợp "ảo giác" trên các đoạn im lặng (silence) thực chất là "artifact" của lớp LLM-evaluator khi cố gắng gán nghĩa cho các đoạn không có thoại. Điều này không phản ánh hoàn toàn năng lực của model ASR.
