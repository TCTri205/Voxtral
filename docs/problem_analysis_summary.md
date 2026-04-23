# Tổng hợp Phân tích Vấn đề Hiệu suất ASR (Voxtral)

Tài liệu này tổng hợp các vấn đề chính ảnh hưởng đến hiệu suất nhận dạng giọng nói, nguyên nhân và các hướng giải pháp đề xuất.

## 1. Các Vấn đề Chính (Problems)

- **Tỷ lệ lỗi cao (CER > 80%):** Nhiều tập tin có kết quả nhận dạng sai lệch hoàn toàn so với thực tế, thường do hiện tượng ảo giác (hallucination).
- **Nhận diện sai ngôn ngữ:** Hệ thống tự động nhận diện nhầm ngôn ngữ khi chất lượng âm thanh kém (ví dụ: tiếng Nhật bị nhận diện thành tiếng Anh).
- **Ngắt lời sớm (Early Truncation):** AI dừng nhận dạng trước khi hội thoại kết thúc, khiến kết quả bị thiếu hụt nghiêm trọng.

## 2. Nguyên nhân Gốc rễ (Causes)

- **Băng thông hẹp (Narrowband):** Âm thanh có tần số thấp (dưới 4kHz) bị mất các chi tiết phụ âm cao, khiến AI không thể phân biệt từ vựng chính xác.
- **Tham số mô hình quá chặt:** Các thiết lập như `beam pruning`, `confidence threshold` và `early-termination logic` đang ở mức quá khắt khe, dễ dẫn đến việc AI "bỏ cuộc" sớm.
- **Thiếu bước tiền xử lý chuyên sâu:** Việc `upsampling` lên 16kHz hiện nay chỉ là nội suy tuyến tính, không giúp phục hồi độ nét thật sự của âm thanh.
- **Phụ thuộc vào nhận diện tự động:** Khác với Javis (thường có gợi ý ngôn ngữ), Voxtral phải tự đoán ngôn ngữ nên dễ bị lạc hướng khi gặp nhiễu.

## 3. Giải pháp Đề xuất (Solutions)

- **Bổ sung AI Restoration:** Tích hợp các mô hình phục hồi băng thông (Audio Super-Resolution/Bandwidth Expansion) để tái tạo các tần số bị mất.
- **Tinh chỉnh tham số:** Nới lỏng các ngưỡng cắt (thresholds) để AI kiên trì hơn trong việc giải mã các đoạn âm thanh khó hoặc có khoảng lặng.
- **Sử dụng Language Hint:** Cung cấp thông tin ngôn ngữ trước (nếu biết) để giảm bớt gánh nặng tính toán và sai sót cho mô hình.
- **Sử dụng Workaround "Dummy Audio":** Đối với phiên bản Realtime (4B) không hỗ trợ tham số `language` trực tiếp, có thể gửi 1-2 giây "âm thanh mồi" (dummy audio) của ngôn ngữ mục tiêu để tạo context biasing trước khi gửi âm thanh chính.
- **Tầng nhận diện ngôn ngữ (LID) độc lập:** Xây dựng một model LID riêng biệt chạy trước Voxtral. Dựa trên kết quả LID và độ tin cậy (confidence score), hệ thống sẽ quyết định đưa vào ASR đa ngôn ngữ hoặc fallback về ngôn ngữ an toàn (ví dụ: tiếng Anh).
- **Tích hợp bộ khử nhiễu (Denoising):** Sử dụng các mô hình như Demucs để tách lọc giọng nói khỏi nhiễu nền trước khi đưa vào ASR.

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

**Kết luận cuối cùng:** Hiệu suất của Voxtral hiện bị giới hạn chủ yếu bởi chất lượng âm thanh đầu vào và việc thiếu định hướng ngôn ngữ. Để vượt qua Javis, Voxtral cần tập trung vào **Cải thiện Tiền xử lý (Pre-processing)** để phục hồi băng thông và **Tối ưu hóa chiến lược Giải mã (Decoding Strategy)** để kiên trì hơn với các đoạn âm thanh khó mà không làm tăng quá mức tỷ lệ ảo giác.
