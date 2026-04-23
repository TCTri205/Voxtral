# Báo cáo Phân tích Chi tiết Từng File: Voxtral vs Javis

Báo cáo này cung cấp cái nhìn chi tiết về hiệu suất của **Voxtral** và **Javis** trên từng tệp âm thanh cụ thể qua cả 10 lần chạy (v1-v10) vào ngày 19/04/2026. Báo cáo này bổ trợ cho báo cáo tổng quát bằng cách phân tích sâu các sai số ở mức độ tệp tin.

## Chỉ số Trung bình Toàn hệ thống

- **Voxtral**: Tỷ lệ Ảo giác trung bình **60.91%**, CER trung bình **45.03%**, Tỷ lệ Chính xác **39.09%**.
- **Javis**: Tỷ lệ Ảo giác trung bình **80.91%**, CER trung bình **34.66%**, Tỷ lệ Chính xác **19.09%**.

## Chú giải

- **H**: Phát hiện Hallucination (ảo giác)
- **OK**: Không có Hallucination
- **(X.X%)**: Tỷ lệ lỗi ký tự (CER)
- **-**: Không có dữ liệu cho lần chạy này

---

## 1. Bảng So sánh Chi tiết Từng File

Bảng này so sánh trực tiếp cả hai hệ thống cho mỗi tệp tin.

| Tên File | Hệ thống | v1 | v2 | v3 | v4 | v5 | v6 | v7 | v8 | v9 | v10 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **media_148280** | **Voxtral** | H (65%) | H (65%) | H (65%) | H (65%) | H (65%) | H (65%) | OK (65%) | OK (65%) | OK (65%) | H (65%) |
| | **Javis** | H (34%) | H (29%) | H (73%) | H (39%) | H (37%) | H (32%) | H (29%) | H (42%) | H (29%) | H (28%) |
| **media_148284** | **Voxtral** | H (16%) | H (16%) | H (16%) | H (16%) | H (16%) | H (16%) | H (16%) | H (16%) | OK (16%) | H (16%) |
| | **Javis** | H (28%) | H (25%) | H (23%) | H (26%) | H (24%) | H (27%) | H (28%) | H (26%) | H (30%) | H (25%) |
| **media_148393** | **Voxtral** | H (18%) | H (18%) | H (18%) | H (18%) | H (18%) | H (18%) | H (18%) | H (18%) | OK (18%) | H (18%) |
| | **Javis** | H (22%) | H (28%) | H (18%) | H (27%) | H (31%) | H (30%) | H (79%) | H (27%) | H (37%) | H (29%) |
| **media_148394** | **Voxtral** | H (34%) | H (34%) | H (34%) | H (34%) | H (34%) | H (34%) | H (34%) | H (34%) | OK (34%) | H (34%) |
| | **Javis** | H (22%) | H (28%) | H (27%) | H (27%) | H (18%) | H (24%) | H (31%) | H (27%) | H (26%) | H (17%) |
| **media_148414** | **Voxtral** | H (100%) | H (100%) | H (100%) | H (100%) | H (100%) | H (100%) | H (100%) | H (100%) | OK (100%) | H (100%) |
| | **Javis** | H (38%) | H (39%) | H (39%) | H (38%) | H (39%) | H (39%) | H (42%) | H (40%) | H (39%) | H (41%) |
| **media_148439** | **Voxtral** | H (35%) | H (35%) | H (35%) | H (35%) | H (35%) | H (35%) | H (35%) | H (35%) | OK (35%) | H (35%) |
| | **Javis** | H (28%) | H (28%) | H (28%) | H (95%) | H (29%) | H (29%) | H (27%) | H (29%) | H (38%) | H (82%) |
| **media_148954** | **Voxtral** | H (69%) | H (69%) | H (69%) | H (69%) | H (69%) | H (69%) | H (69%) | OK (69%) | OK (69%) | H (69%) |
| | **Javis** | H (30%) | H (34%) | H (30%) | H (29%) | H (93%) | H (29%) | H (62%) | H (30%) | H (34%) | H (35%) |
| **media_149291** | **Voxtral** | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) | OK (98%) |
| | **Javis** | H (153%) | H (182%) | H (20%) | OK (159%) | H (170%) | H (19%) | H (21%) | H (154%) | H (19%) | H (20%) |
| **media_149733** | **Voxtral** | H (60%) | H (60%) | H (60%) | H (60%) | H (60%) | H (60%) | OK (60%) | OK (60%) | OK (60%) | H (60%) |
| | **Javis** | H (52%) | H (41%) | H (48%) | H (50%) | H (65%) | H (46%) | H (38%) | H (42%) | H (42%) | H (51%) |
| **silence_60s** | **Voxtral** | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) |
| | **Javis** | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) |
| **stoch_noise** | **Voxtral** | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) |
| | **Javis** | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) | OK (0%) |

---

## 2. Thống kê Tổng quát (Overall Statistics)

Dựa trên dữ liệu từ 20 lượt đánh giá (10 lượt/hệ thống), chúng ta có bảng phân bổ lỗi trung bình mỗi lượt chạy:

| Chỉ số | Voxtral | Javis | Xác suất (Mỗi file-run) |
| :--- | :---: | :---: | :---: |
| **Phát hiện hoàn hảo (None Error)** | 4.3 | 2.1 | Voxtral: **39.09%** \| Javis: 19.09% |
| **Lỗi Chèn thêm (Insertion)** | **6.0** | 8.7 | Voxtral: **54.54%** \| Javis: 79.09% |
| **Lỗi Thay thế nội dung** | 0.7 | 0.2 | Voxtral: 6.36% \| Javis: 1.81% |
| **Lỗi Im lặng (Silence Text)** | 0.0 | 0.0 | 0.00% (Sạch hoàn toàn) |
| **Lẫn ngôn ngữ (Language Mix)** | *Hiếm* | **Rất nhiều** | ~8% vs ~17% |

---

## 3. Quan sát Chính từ Bảng Dữ liệu

### Đặc điểm Cải thiện của Voxtral

- **Voxtral** cho thấy trạng thái "sạch" rõ rệt ở lần chạy **v9**, khi tất cả các lỗi hallucination đột ngột biến mất (trạng thái OK). Tuy nhiên, CER vẫn ở mức cao và không đổi (ví dụ: 65,49% cho `media_148280`), cho thấy mặc dù ảo giác được kiểm soát, độ chính xác phiên âm cho lời nói thực tế có thể không được cải thiện trong chế độ chạy cụ thể đó.
- **Voxtral** liên tục đạt trạng thái "sạch" trên các đoạn im lặng (`silence_60s`) sau khi hiệu chỉnh nhãn đúng với CER 0%.

### Sự không ổn định của Javis

- **Javis** cho thấy sự nhạy cảm lớn với tiếng ồn và sự im lặng trong các bản build cũ, nhưng sau khi chuẩn hóa, tỷ lệ "OK" (không ảo giác) đã tăng lên ở các file không chứa lời nói (silence, noise). CER của Javis dao động đáng kể giữa các lần chạy cho cùng một tệp, trong khi CER của Voxtral ổn định hơn.
- **Lưu ý về Looping**: Javis không tự tạo ra văn bản khi file âm thanh hoàn toàn im lặng từ đầu (Lỗi Silence Text = 0.0). Tuy nhiên, khi gặp khoảng lặng (pause) giữa chừng trong một cuộc hội thoại, Javis rất dễ bị "kẹt" và lặp lại các từ trước đó (looping). Hành vi này được phản ánh rõ qua chỉ số **Lỗi Chèn thêm (Insertion)** cực cao của Javis.

### Các Tệp tin Nguy cơ Cao

- `media_149291` là điểm thất bại lớn của **Javis**, với CER vượt quá **150%** trong nhiều lần chạy (v1, v2, v4, v5, v8), do các ảo giác ngoại ngữ (tiếng Hàn/Nhật lẫn lộn).
- `media_148414` liên tục dẫn đến **CER 100%** cho **Voxtral**, nhưng CER thấp hơn (**~40%**) cho **Javis**, mặc dù cả hai đều gặp lỗi ảo giác. Điều này cho thấy ảo giác của Javis trên tệp này có thể vô tình trùng khớp nhiều hơn với các ký tự trong ground truth hoặc nó thu thập được một số lời nói mà Voxtral bỏ lỡ hoàn toàn.

### Nghịch lý CER vs Hallucination

Một phát hiện quan trọng là **Javis có CER tốt hơn (34.66%)** so với Voxtral (45.03%), nhưng lại có **tỷ lệ ảo giác cao hơn nhiều (80.91%)**. Điều này chỉ ra rằng:

1. Khi không bị ảo giác, Javis bám sát âm thanh gốc tốt hơn Voxtral.
2. Hoặc, các đoạn ảo giác của Javis (thường là tiếng Hàn/Nhật lặp lại) vô tình chứa các ký tự trùng lặp với ground truth, làm giảm CER về mặt toán học nhưng lại làm hỏng chất lượng ngữ nghĩa của bản dịch.
3. **Voxtral** ưu tiên sự "sạch sẽ" (nhiều bản dịch hoàn hảo hơn), nhưng khi sai thì thường sai lệch lớn về mặt ký tự (CER cao).

---

## 4. Phân tích Chi tiết và Mức độ Ảo giác (Hallucination Depth Analysis)

Phần này đi sâu vào bản chất của các lỗi ảo giác để hiểu rõ hơn về mức độ ảnh hưởng của chúng đến chất lượng hội thoại.

### Phân loại và Mức độ Nghiêm trọng

- **Mức độ Trung bình (Medium)**: Thêm các cụm từ đệm, câu chào hỏi lịch sự nhưng không có trong âm thanh gốc (ví dụ: "Cảm ơn", "Làm phiền bạn"). Không làm thay đổi hoàn toàn nội dung nhưng gây nhiễu.
- **Mức độ Cao (High)**: Tạo ra các nội dung hoàn toàn không liên quan, nhầm lẫn ngôn ngữ (tiếng Hàn/Nhật), hoặc tự bịa ra những câu hội thoại dài khi âm thanh thực tế là im lặng hoặc tiếng ồn.

### Chi tiết theo Hệ thống

#### Voxtral: Ảo giác Kính ngữ và Lời chào máy móc

Ảo giác của Voxtral tập trung nhiều nhất vào việc thêm các cụm từ lịch sự kiểu Nhật (Keigo) một cách máy móc.

- **media_148280**: Thường xuyên thêm *"お茶になっております"* (Tôi xin lỗi/đang phục vụ trà) hoặc *"司法様団体"* (Tổ chức tư pháp) - những từ hoàn toàn không có trong ground truth.
- **media_148439 (High)**: Tự tạo ra đoạn chào hỏi dài: *"こんにちは、遠隔の指標者の坂本です。生徒キャパン、熊谷でございます..."* trong khi âm thanh gốc chỉ có thông tin công ty đơn giản.
- **media_148414 (High)**: Bị kẹt vào một câu tiếng Anh lạc lõng: *"Hi, Joseph. I'm sorry."* dù âm thanh là tiếng Nhật.

#### Javis: Ảo giác Đa ngôn ngữ và Sáng tạo

Javis có mức độ ảo giác nặng hơn, thường xuyên "mơ" ra các đoạn hội thoại bằng ngôn ngữ khác hoặc lặp lại vô tận.

- **media_149291 (High)**: Điểm yếu lớn nhất. Javis liên tục "nói" tiếng Hàn dài dằng dặc: *"무엇을 도와드릴까요? 네, 감사합니다..."* (Tôi có thể giúp gì cho bạn? Vâng, cảm ơn...).
- **media_148954 (High)**: Lẫn lộn Hàn-Nhật: *"あげてくださいね. 수고하십니다. 그러세요.いります..."*
- **media_148414**: Hay bị lặp (looping) các câu khẳng định: *"はい、ありがとうございます。はい、ありがとうございます。..."*

### Tổng kết Loại lỗi & Xác suất

| Loại Ảo giác | Voxtral (Prob) | Javis (Prob) | Nhận xét |
| :--- | :---: | :---: | :--- |
| **Insertion** (Chèn thêm) | **54.54%** | **79.09%** | Javis cực kỳ phổ biến |
| **Replacement** (Thay thế) | **6.36%** | **1.81%** | Voxtral cao hơn 3.5 lần |
| **Language Mix** (Hàn-Nhật) | **~8.18%** | **~17.27%** | Javis bị kẹt ngôn ngữ thường xuyên |
| **Silence Text** (Lỗi Im lặng) | **0.00%** | **0.00%** | Đã sạch sau hiệu chỉnh |

---
*Báo cáo được tạo dựa trên 220 điểm đánh giá file-run và phân tích chi tiết từng evidence.*
